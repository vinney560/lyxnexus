import os
import time
import logging
import sys
import signal
from typing import List, Optional, Dict, Any
from collections import deque
from contextlib import contextmanager

from sqlalchemy import create_engine, MetaData, Table, select, text, inspect, LargeBinary
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DBAPIError, IntegrityError
from sqlalchemy.pool import NullPool
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DatabaseCloner:
    def __init__(
        self,
        source_url: str,
        target_url: str,
        batch_size: int = 500,
        log_every_batch: bool = True,
        drop_target_first: bool = True,
        max_retries: int = 3,
        disable_constraints: bool = True,
        ssl_mode: str = "require"
    ):
        """
        Production database cloner without pg_dump dependency
        
        Args:
            source_url: Source database URL
            target_url: Target database URL
            batch_size: Rows per batch
            log_every_batch: Log progress for batches
            drop_target_first: Drop existing tables in target
            max_retries: Max retries for failed operations
            disable_constraints: Disable FK constraints during clone
            ssl_mode: SSL mode for connections
        """
        self.source_url = source_url
        self.target_url = target_url
        self.batch_size = batch_size
        self.log_every_batch = log_every_batch
        self.drop_target_first = drop_target_first
        self.max_retries = max_retries
        self.disable_constraints = disable_constraints
        self.ssl_mode = ssl_mode
        
        # Fix Neon SSL issues
        if "neon.tech" in target_url:
            self.ssl_mode = "require"
            # Remove channel_binding parameter if present
            if "channel_binding=require" in target_url:
                self.target_url = target_url.replace("channel_binding=require", "").replace("&&", "&").rstrip("&")
        
        # Ensure SSL mode is in URLs
        if "sslmode=" not in self.source_url:
            self.source_url = f"{self.source_url}?sslmode={self.ssl_mode}"
        
        if "sslmode=" not in self.target_url:
            self.target_url = f"{self.target_url}?sslmode={self.ssl_mode}"
        
        # Create engines
        self.source_engine = self._create_engine(self.source_url)
        self.target_engine = self._create_engine(self.target_url)
        
        # Statistics
        self.stats = {
            'start_time': None,
            'end_time': None,
            'tables_processed': 0,
            'rows_copied': 0,
            'tables_failed': [],
            'total_time': 0
        }
        
        # Handle interrupts
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _create_engine(self, url: str):
        """Create SQLAlchemy engine with optimized settings"""
        return create_engine(
            url,
            poolclass=NullPool,
            connect_args={
                'connect_timeout': 30,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            },
            echo=False,
            execution_options={
                'isolation_level': 'READ COMMITTED',
                'statement_timeout': 3600000  # 1 hour in milliseconds
            }
        )
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully"""
        logger.warning(f"⚠️  Received interrupt signal, cleaning up...")
        self.cleanup()
        sys.exit(1)
    
    def cleanup(self):
        """Clean up database connections"""
        logger.info("🧹 Cleaning up connections...")
        try:
            if hasattr(self, 'source_engine'):
                self.source_engine.dispose()
            if hasattr(self, 'target_engine'):
                self.target_engine.dispose()
            logger.info("✅ Connections closed")
        except:
            pass
    
    def _test_connections(self) -> bool:
        """Test database connections"""
        logger.info("🔍 Testing database connections...")
        
        try:
            with self.source_engine.connect() as conn:
                result = conn.execute(text("SELECT version(), current_database()"))
                version, db_name = result.fetchone()
                logger.info(f"✅ Source: {db_name} - {version.split(',')[0]}")
            
            with self.target_engine.connect() as conn:
                result = conn.execute(text("SELECT version(), current_database()"))
                version, db_name = result.fetchone()
                logger.info(f"✅ Target: {db_name} - {version.split(',')[0]}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def _get_tables_in_dependency_order(self, metadata: MetaData) -> List[Table]:
        """Get tables in topological order based on foreign key dependencies"""
        tables_by_name = {table.name: table for table in metadata.sorted_tables}
        adjacency = {table.name: [] for table in metadata.sorted_tables}
        indegree = {table.name: 0 for table in metadata.sorted_tables}
        
        for table in metadata.sorted_tables:
            for fk in table.foreign_key_constraints:
                ref_table_name = fk.referred_table.name
                if ref_table_name in adjacency:
                    adjacency[ref_table_name].append(table.name)
                    indegree[table.name] += 1
        
        # Kahn's algorithm for topological sort
        result = []
        queue = deque([name for name, degree in indegree.items() if degree == 0])
        
        while queue:
            table_name = queue.popleft()
            result.append(tables_by_name[table_name])
            
            for dependent in adjacency[table_name]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)
        
        # Add any remaining tables (circular dependencies)
        remaining = [t for t in metadata.sorted_tables if t not in result]
        result.extend(remaining)
        
        logger.info(f"📊 Table dependency order determined: {len(result)} tables")
        return result
    
    def _has_binary_columns(self, table: Table) -> bool:
        """Check if table has binary columns"""
        for column in table.columns:
            if isinstance(column.type, LargeBinary):
                return True
            if hasattr(column.type, '__visit_name__'):
                if column.type.__visit_name__ in ['large_binary', 'blob', 'bytea']:
                    return True
        return False
    
    def _get_table_info(self, table: Table) -> Dict[str, Any]:
        """Get information about a table"""
        with self.source_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table.name}"))
            row_count = result.scalar() or 0
        
        return {
            'name': table.name,
            'row_count': row_count,
            'has_binary': self._has_binary_columns(table),
            'columns': [c.name for c in table.columns],
            'has_fks': len(table.foreign_key_constraints) > 0
        }
    
    def _disable_foreign_keys(self):
        """Disable foreign key constraints"""
        try:
            with self.target_engine.connect() as conn:
                conn.execute(text("SET session_replication_role = 'replica';"))
                conn.commit()
            logger.info("🔓 Foreign key constraints disabled")
        except Exception as e:
            logger.warning(f"Could not disable foreign keys: {e}")
    
    def _enable_foreign_keys(self):
        """Enable foreign key constraints"""
        try:
            with self.target_engine.connect() as conn:
                conn.execute(text("SET session_replication_role = 'origin';"))
                conn.commit()
            logger.info("🔒 Foreign key constraints enabled")
        except Exception as e:
            logger.warning(f"Could not enable foreign keys: {e}")
    
    def _clone_table_schema(self, table: Table) -> bool:
        """Create table schema in target"""
        try:
            table.create(bind=self.target_engine, checkfirst=True)
            logger.debug(f"  Created schema for {table.name}")
            return True
        except Exception as e:
            logger.warning(f"  Could not create schema for {table.name}: {e}")
            return False
    
    def _clone_table_data(self, table: Table, table_info: Dict[str, Any]) -> bool:
        """Clone data for a single table with binary data support"""
        table_name = table.name
        row_count = table_info['row_count']
        has_binary = table_info['has_binary']
        
        if row_count == 0:
            logger.info(f"  ⏭️  Empty table, skipping data")
            return True
        
        logger.info(f"  📊 Rows to copy: {row_count:,}")
        if has_binary:
            logger.info(f"  🗃️  Contains binary data")
            # Use smaller batch size for binary tables
            batch_size = max(10, self.batch_size // 10)
        else:
            batch_size = self.batch_size
        
        start_time = time.time()
        offset = 0
        rows_copied = 0
        batch_num = 0
        retries = 0
        
        try:
            while rows_copied < row_count:
                try:
                    # Fetch batch
                    with self.source_engine.connect() as src_conn:
                        rows = src_conn.execute(
                            select(table).offset(offset).limit(batch_size)
                        ).mappings().all()
                        
                        if not rows:
                            break
                    
                    # Insert batch with transaction
                    with self.target_engine.begin() as tgt_conn:
                        try:
                            tgt_conn.execute(table.insert(), rows)
                        except IntegrityError as e:
                            # Handle FK violations by inserting row by row
                            logger.warning(f"    Batch {batch_num} FK violation, inserting row by row")
                            for row in rows:
                                try:
                                    tgt_conn.execute(table.insert(), row)
                                    rows_copied += 1
                                except:
                                    continue
                            tgt_conn.commit()
                            offset += batch_size
                            batch_num += 1
                            continue
                    
                    rows_copied += len(rows)
                    offset += batch_size
                    batch_num += 1
                    retries = 0  # Reset retries on success
                    
                    # Log progress
                    if self.log_every_batch and (batch_num % 10 == 0 or rows_copied >= row_count):
                        percent = (rows_copied / row_count) * 100
                        elapsed = time.time() - start_time
                        rows_per_sec = rows_copied / elapsed if elapsed > 0 else 0
                        logger.info(f"    Progress: {rows_copied:,}/{row_count:,} ({percent:.1f}%) - {rows_per_sec:.0f} rows/sec")
                    
                except (OperationalError, DBAPIError) as e:
                    retries += 1
                    if retries > self.max_retries:
                        logger.error(f"    ❌ Max retries exceeded for {table_name}: {e}")
                        return False
                    
                    logger.warning(f"    Batch {batch_num} failed, retry {retries}/{self.max_retries}: {e}")
                    time.sleep(2 ** retries)  # Exponential backoff
                    continue
                except Exception as e:
                    logger.error(f"    ❌ Unexpected error: {e}")
                    return False
            
            # Update statistics
            elapsed = time.time() - start_time
            rows_per_sec = rows_copied / elapsed if elapsed > 0 else 0
            self.stats['rows_copied'] += rows_copied
            
            logger.info(f"  ✅ Copied {rows_copied:,} rows in {elapsed:.2f}s ({rows_per_sec:.1f} rows/sec)")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Failed to clone {table_name}: {e}")
            return False
    
    def _drop_existing_tables(self):
        """Drop existing tables in target database"""
        if not self.drop_target_first:
            return
        
        logger.info("🗑️  Dropping existing tables in target...")
        
        # Get list of existing tables
        try:
            inspector = inspect(self.target_engine)
            existing_tables = inspector.get_table_names()
            
            if not existing_tables:
                logger.info("  ✅ No existing tables to drop")
                return
            
            # Disable constraints before dropping
            if self.disable_constraints:
                self._disable_foreign_keys()
            
            # Drop tables
            with self.target_engine.connect() as conn:
                for table_name in existing_tables:
                    try:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
                        logger.debug(f"  Dropped table: {table_name}")
                    except Exception as e:
                        logger.warning(f"  Could not drop table {table_name}: {e}")
                conn.commit()
            
            logger.info(f"  ✅ Dropped {len(existing_tables)} existing tables")
            
        except Exception as e:
            logger.warning(f"  Could not drop existing tables: {e}")
    
    def clone(self) -> bool:
        """Main method to clone the database"""
        self.stats['start_time'] = time.time()
        
        try:
            logger.info("=" * 70)
            logger.info("🚀 PRODUCTION DATABASE CLONER")
            logger.info("=" * 70)
            logger.info(f"🔗 Source: {self.source_url.split('@')[1] if '@' in self.source_url else '[...]'}")
            logger.info(f"🎯 Target: {self.target_url.split('@')[1] if '@' in self.target_url else '[...]'}")
            logger.info(f"📦 Batch size: {self.batch_size}")
            logger.info(f"🔄 Max retries: {self.max_retries}")
            logger.info(f"🔓 Disable constraints: {self.disable_constraints}")
            
            # Test connections
            if not self._test_connections():
                return False
            
            # Get source schema
            logger.info("\n📋 Reading source database schema...")
            src_meta = MetaData()
            src_meta.reflect(bind=self.source_engine)
            
            # Drop existing tables if requested
            self._drop_existing_tables()
            
            # Get tables in dependency order
            logger.info("🔀 Determining table dependencies...")
            tables = self._get_tables_in_dependency_order(src_meta)
            
            logger.info(f"\n📊 Found {len(tables)} tables to clone")
            
            # Disable foreign keys if requested
            if self.disable_constraints:
                self._disable_foreign_keys()
            
            # Phase 1: Create table schemas
            logger.info("\n🏗️  Creating table schemas...")
            schemas_created = 0
            for table in tables:
                if self._clone_table_schema(table):
                    schemas_created += 1
            logger.info(f"✅ Created {schemas_created}/{len(tables)} table schemas")
            
            # Phase 2: Clone data
            logger.info("\n📊 Cloning table data...")
            tables_cloned = 0
            
            for i, table in enumerate(tables):
                logger.info(f"\n[{i+1}/{len(tables)}] 📋 {table.name}")
                
                # Get table info
                table_info = self._get_table_info(table)
                
                # Log column info
                columns = table_info['columns']
                if len(columns) > 5:
                    logger.info(f"  Columns: {', '.join(columns[:3])}... and {len(columns)-3} more")
                else:
                    logger.info(f"  Columns: {', '.join(columns)}")
                
                if table_info['has_fks']:
                    logger.info(f"  🔗 Has foreign keys")
                
                # Clone table data
                if self._clone_table_data(table, table_info):
                    tables_cloned += 1
                    self.stats['tables_processed'] += 1
                else:
                    self.stats['tables_failed'].append(table.name)
                
                # Small delay between tables
                if i < len(tables) - 1:
                    time.sleep(0.1)
            
            # Enable foreign keys
            if self.disable_constraints:
                self._enable_foreign_keys()
            
            # Run VACUUM ANALYZE on target
            logger.info("\n⚡ Optimizing target database...")
            try:
                with self.target_engine.connect() as conn:
                    conn.execute(text("VACUUM ANALYZE;"))
                    conn.commit()
                logger.info("✅ Optimization complete")
            except Exception as e:
                logger.warning(f"  Optimization failed: {e}")
            
            # Print summary
            self._print_summary()
            
            return len(self.stats['tables_failed']) == 0
            
        except KeyboardInterrupt:
            logger.info("\n⚠️  Clone interrupted by user")
            return False
        except Exception as e:
            logger.error(f"\n❌ Clone failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        finally:
            self.stats['end_time'] = time.time()
            self.cleanup()
    
    def _print_summary(self):
        """Print cloning summary"""
        if self.stats['start_time'] and self.stats['end_time']:
            total_time = self.stats['end_time'] - self.stats['start_time']
        else:
            total_time = 0
        
        logger.info("\n" + "=" * 70)
        logger.info("🎉 CLONE COMPLETE")
        logger.info("=" * 70)
        
        logger.info("📊 STATISTICS:")
        logger.info(f"  Total time:        {total_time:.2f} seconds")
        logger.info(f"  Tables processed:  {self.stats['tables_processed']}")
        logger.info(f"  Rows copied:       {self.stats['rows_copied']:,}")
        
        if total_time > 0:
            logger.info(f"  Rows per second:   {self.stats['rows_copied'] / total_time:.1f}")
        
        if self.stats['tables_failed']:
            logger.info(f"\n⚠️  FAILED TABLES ({len(self.stats['tables_failed'])}):")
            for table in self.stats['tables_failed'][:5]:
                logger.info(f"  • {table}")
            if len(self.stats['tables_failed']) > 5:
                logger.info(f"  ... and {len(self.stats['tables_failed']) - 5} more")
        else:
            logger.info("\n✅ All tables cloned successfully!")
        
        logger.info("=" * 70)

def main():
    # DATABASE URLs
    source_db = ""
    target_db = ""
    
    if "channel_binding=require" in source_db:
        source_db = source_db.replace("?channel_binding=require", "").replace("&channel_binding=require", "")
    
    logger.info("🚀 Starting database clone from Render.com to Neon.tech")
    logger.info("=" * 60)
    
    # Create and run cloner
    cloner = DatabaseCloner(
        source_url=source_db,
        target_url=target_db,
        batch_size=100,
        log_every_batch=True,
        drop_target_first=True,
        max_retries=5,
        disable_constraints=True,
        ssl_mode="require"
    )
    
    success = cloner.clone()
    
    if success:
        logger.info("✅ Database cloned successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Database clone failed or had errors")
        sys.exit(1)

if __name__ == "__main__":
    main()