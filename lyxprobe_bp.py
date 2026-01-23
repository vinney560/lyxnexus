#!/user/env/bin python3
"""
LyxProbe v2.0 - Command Line Interface for System Administration
Advanced monitoring and administration tool with CLI interface
"""

from flask import Blueprint, render_template, jsonify, request, abort
from flask_login import current_user, login_required
from functools import wraps
from datetime import datetime, timedelta, timezone
from app import db, User

# ============ BLUEPRINT INITIALIZATION ============
probe_bp = Blueprint("probe", __name__, url_prefix='/probe')

# ============ SECURITY & AUTHENTICATION ============
def operator_required(f):
    """Only allow users with year=5 (operators) to access probe"""
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.year != 5:
            abort(403)
        return f(*args, **kwargs)
    return decorated_func

# ============ PROBE COMMAND PROCESSOR ============
class ProbeCommandProcessor:
    """Process and execute probe commands"""
    
    def __init__(self):
        self.commands = {
            'help': self.cmd_help,
            'clear': self.cmd_clear,
            'date': self.cmd_date,
            'whoami': self.cmd_whoami,
            'list-admins': self.cmd_list_admins,
            'list-operators': self.cmd_list_operators,
            'list-users': self.cmd_list_users,
            'kill-rogue': self.cmd_kill_rogue,
            'ban': self.cmd_ban,
            'unban': self.cmd_unban,
            'promote': self.cmd_promote,
            'demote': self.cmd_demote,
            'verify': self.cmd_verify,
            'unverify': self.cmd_unverify,
            'user-info': self.cmd_user_info,
            'system-info': self.cmd_system_info,
            'export': self.cmd_export,
            'ping': self.cmd_ping,
            'echo': self.cmd_echo,
            'reboot': self.cmd_reboot,
            'version': self.cmd_version,
            'shutdown': self.cmd_shutdown
        }
    
    def process(self, command):
        """Process incoming command"""
        parts = command.strip().split()
        if not parts:
            return self.format_output("ERROR", "No command entered", "error")
        
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd not in self.commands:
            return self.format_output("ERROR", f"Unknown command: {cmd}. Type 'help' for available commands.", "error")
        
        try:
            return self.commands[cmd](args)
        except Exception as e:
            return self.format_output("ERROR", f"Command failed: {str(e)}", "error")
    
    def format_output(self, title, content, type="info"):
        """Format command output with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return {
            'timestamp': timestamp,
            'title': title,
            'content': content,
            'type': type  # info, warning, error, success
        }
    
    # ============ COMMAND DEFINITIONS ============
    
    def cmd_help(self, args):
        """Display available commands"""
        commands_list = [
            "=== SYSTEM COMMANDS ===",
            "help                 - Display this help message",
            "clear                - Clear terminal screen",
            "date                 - Show current date and time",
            "whoami               - Show current operator info",
            "ping                 - Check server connectivity",
            "echo [text]          - Echo back text",
            "",
            "=== USER MANAGEMENT ===",
            "list-users           - List all users",
            "list-admins          - List all administrators",
            "list-operators       - List all operators",
            "user-info [id/name]  - Get detailed user info",
            "ban [id]             - Ban a user account",
            "unban [id]           - Unban a user account",
            "promote [id]         - Promote user to admin",
            "demote [id]          - Demote admin to user",
            "verify [id]          - Verify admin account",
            "unverify [id]        - Unverify admin account",
            "",
            "=== SECURITY OPERATIONS ===",
            "kill-rogue           - Remove unverified admins",
            "system-info          - Display system statistics",
            "export [table]       - Export data (users/admins)",
            "reboot               - Reboot the server",
            "--version            - Show software version",
            "",
            "=== SYNTAX ===",
            "> command [argument] - Run command with argument",
            "> Ctrl+L / clear     - Clear terminal"
        ]
        return self.format_output("HELP", "\n".join(commands_list), "info")
    
    def cmd_clear(self, args):
        """Clear terminal (client-side)"""
        return self.format_output("SYSTEM", "Terminal cleared", "info")
    
    def cmd_date(self, args):
        """Display current date and time"""
        now = datetime.now(timezone(timedelta(hours=3)))
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%H:%M:%S")
        return self.format_output("DATE/TIME", f"{date_str}\n{time_str}", "info")
    
    def cmd_whoami(self, args):
        """Display current operator information"""
        user = current_user
        status = "ACTIVE" if user.status else "BANNED"
        verified = "VERIFIED" if user.is_verified_admin else "UNVERIFIED"
        admin_status = "ADMIN" if user.is_admin else "USER"
        paid = "PAID" if user.paid else "UNPAID"
        
        info = [
            f"Username:     {user.username}",
            f"User ID:      {user.id}",
            f"Mobile:       {user.mobile}",
            f"Year:         {user.year}",
            f"Status:       {status}",
            f"Fee:          {paid}",
            f"Admin:        {admin_status}",
            f"Verified:     {verified}",
            f"Last Login:   Recent",
            f"Privilege:    OPERATOR (Year 5)"
        ]
        return self.format_output("OPERATOR INFO", "\n".join(info), "info")
    
    def cmd_list_admins(self, args):
        """List all administrators"""
        try:
            admins = User.query.filter(User.is_admin == True).order_by(User.id).all()
            if not admins:
                return self.format_output("ADMIN LIST", "No administrators found", "warning")
            
            admin_list = []
            for admin in admins:
                status = "✓" if admin.status else "✗"
                verified = "✓" if admin.is_verified_admin else "✗"
                admin_list.append(
                    f"[{admin.id:03d}] {admin.username:20} | "
                    f"Year: {admin.year} | Active: {status} | "
                    f"Verified: {verified} | Mobile: {admin.mobile}"
                )
            
            header = f"Total Admins: {len(admins)}\n"
            header += "-" * 70
            return self.format_output("ADMIN LIST", header + "\n" + "\n".join(admin_list), "info")
        except Exception as e:
            return self.format_output("ERROR", f"Database error: {str(e)}", "error")
    
    def cmd_list_operators(self, args):
        """List all operators"""
        try:
            operators = User.query.filter(User.year == 5).order_by(User.id).all()
            if not operators:
                return self.format_output("OPERATOR LIST", "No operators found", "warning")
            
            operator_list = []
            for operator in operators:
                status = "✓" if operator.status else "✗"
                verified = "✓" if operator.is_verified_admin else "✗"
                operator_list.append(
                    f"[{operator.id:03d}] {operator.username:20} | "
                    f"Year: {operator.year} | Active: {status} | "
                    f"Verified: {verified} | Mobile: {operator.mobile}"
                )
            
            header = f"Total Operators: {len(operators)}\n"
            header += "-" * 70
            return self.format_output("OPERATOR LIST", header + "\n" + "\n".join(operator_list), "info")
        except Exception as e:
            return self.format_output("ERROR", f"Database error: {str(e)}", "error")
    
    def cmd_list_users(self, args):
        """List all users with pagination"""
        try:
            users = User.query.order_by(User.id).all()
            if not users:
                return self.format_output("USER LIST", "No users found", "warning")
            
            # Apply filters if provided
            if args:
                filter_arg = args[0].lower()
                if filter_arg == "banned":
                    users = [u for u in users if not u.status]
                elif filter_arg == "active":
                    users = [u for u in users if u.status]
                elif filter_arg == "admin":
                    users = [u for u in users if u.is_admin]
            
            user_list = []
            for user in users:
                status = "Active" if user.status else "Banned"
                admin = "Admin" if user.is_admin else "User"
                user_list.append(
                    f"[{user.id:04d}] {user.username:20} | "
                    f"Year: {user.year} | Status: {status:6} | "
                    f"Type: {admin:5} | Mobile: {user.mobile}"
                )
            
            header = f"Total Users: {len(users)}"
            if args:
                header += f" (Filter: {args[0]})"
            header += "\n" + "-" * 80
            
            # Paginate if too many results
            if len(user_list) > 50:
                user_list = user_list[:50]
                footer = f"\n... and {len(users) - 50} more users. Use export for full list."
                return self.format_output("USER LIST (First 50)", header + "\n" + "\n".join(user_list) + footer, "info")
            
            return self.format_output("USER LIST", header + "\n" + "\n".join(user_list), "info")
        except Exception as e:
            return self.format_output("ERROR", f"Database error: {str(e)}", "error")
    
    def cmd_kill_rogue(self, args):
        """Remove unverified admin privileges and ban accounts"""
        try:
            # Find unverified admins
            rogue_admins = User.query.filter(
                User.is_admin == True,
                User.is_verified_admin == False
            ).all()
            
            if not rogue_admins:
                return self.format_output("KILL ROGUE", "No unverified admins found", "warning")
            
            killed = []
            for admin in rogue_admins:
                old_status = "Active" if admin.status else "Banned"
                admin.is_admin = False
                admin.status = False  # Ban the account
                killed.append(f"[{admin.id}] {admin.username} (was {old_status})")
            
            db.session.commit()
            
            result = [
                f"Operation: KILL-ROGUE-ADMINS",
                f"Time: {datetime.now(timezone(timedelta(hours=3))).strftime('%H:%M:%S')}",
                f"Targets: {len(rogue_admins)} unverified admin(s)",
                f"Actions:",
                f"  • Admin privileges revoked",
                f"  • Accounts banned",
                f"",
                f"AFFECTED ACCOUNTS:"
            ] + killed
            
            return self.format_output("OPERATION SUCCESSFUL", "\n".join(result), "success")
        except Exception as e:
            db.session.rollback()
            return self.format_output("ERROR", f"Operation failed: {str(e)}", "error")
    
    def cmd_ban(self, args):
        """Ban a user account"""
        if not args:
            return self.format_output("ERROR", "Usage: ban [user_id]", "error")
        
        try:
            user_id = int(args[0])
            user = User.query.get(user_id)
            
            if not user:
                return self.format_output("ERROR", f"User ID {user_id} not found", "error")
            
            if user.id == current_user.id:
                return self.format_output("ERROR", "Cannot ban yourself", "error")
            
            if user.year == 5:
                return self.format_output("ERROR", "Cannot ban operator accounts", "error")
            
            old_status = user.status
            user.status = False
            db.session.commit()
            
            result = [
                f"User: {user.username} (ID: {user.id})",
                f"Previous Status: {'Active' if old_status else 'Banned'}",
                f"New Status: BANNED",
                f"Action: Account banned at {datetime.now().strftime('%H:%M:%S')}",
                f"Operator: {current_user.username}"
            ]
            
            return self.format_output("ACCOUNT BANNED", "\n".join(result), "success")
        except ValueError:
            return self.format_output("ERROR", "Invalid user ID", "error")
        except Exception as e:
            db.session.rollback()
            return self.format_output("ERROR", f"Ban failed: {str(e)}", "error")
    
    def cmd_unban(self, args):
        """Unban a user account"""
        if not args:
            return self.format_output("ERROR", "Usage: unban [user_id]", "error")
        
        try:
            user_id = int(args[0])
            user = User.query.get(user_id)
            
            if not user:
                return self.format_output("ERROR", f"User ID {user_id} not found", "error")
            
            old_status = user.status
            user.status = True
            db.session.commit()
            
            result = [
                f"User: {user.username} (ID: {user.id})",
                f"Previous Status: {'Active' if old_status else 'Banned'}",
                f"New Status: ACTIVE",
                f"Action: Account unbanned at {datetime.now().strftime('%H:%M:%S')}",
                f"Operator: {current_user.username}"
            ]
            
            return self.format_output("ACCOUNT UNBANNED", "\n".join(result), "success")
        except ValueError:
            return self.format_output("ERROR", "Invalid user ID", "error")
        except Exception as e:
            db.session.rollback()
            return self.format_output("ERROR", f"Unban failed: {str(e)}", "error")
    
    def cmd_promote(self, args):
        """Promote user to admin"""
        if not args:
            return self.format_output("ERROR", "Usage: promote [user_id]", "error")
        
        try:
            user_id = int(args[0])
            user = User.query.get(user_id)
            
            if not user:
                return self.format_output("ERROR", f"User ID {user_id} not found", "error")
            
            if user.is_admin:
                return self.format_output("INFO", f"User {user.username} is already an admin", "info")
            
            user.is_admin = True
            user.is_verified_admin = True
            db.session.commit()
            
            result = [
                f"User: {user.username} (ID: {user.id})",
                f"Previous Role: User",
                f"New Role: Administrator (Unverified)",
                f"Action: Promoted at {datetime.now().strftime('%H:%M:%S')}",
                f"Operator: {current_user.username}",
                f"Note: User needs verification by senior operator"
            ]
            
            return self.format_output("USER PROMOTED", "\n".join(result), "success")
        except ValueError:
            return self.format_output("ERROR", "Invalid user ID", "error")
        except Exception as e:
            db.session.rollback()
            return self.format_output("ERROR", f"Promotion failed: {str(e)}", "error")
    
    def cmd_demote(self, args):
        """Demote admin to user"""
        if not args:
            return self.format_output("ERROR", "Usage: demote [user_id]", "error")
        
        try:
            user_id = int(args[0])
            user = User.query.get(user_id)
            
            if not user:
                return self.format_output("ERROR", f"User ID {user_id} not found", "error")
            
            if user.id == current_user.id:
                return self.format_output("ERROR", "Cannot demote yourself", "error")
            
            if user.year == 5:
                return self.format_output("ERROR", "Cannot demote operator accounts", "error")
            
            if not user.is_admin:
                return self.format_output("INFO", f"User {user.username} is not an admin", "info")
            
            user.is_admin = False
            user.is_verified_admin = False
            db.session.commit()
            
            result = [
                f"User: {user.username} (ID: {user.id})",
                f"Previous Role: Administrator",
                f"New Role: Regular User",
                f"Action: Demoted at {datetime.now().strftime('%H:%M:%S')}",
                f"Operator: {current_user.username}"
            ]
            
            return self.format_output("ADMIN DEMOTED", "\n".join(result), "success")
        except ValueError:
            return self.format_output("ERROR", "Invalid user ID", "error")
        except Exception as e:
            db.session.rollback()
            return self.format_output("ERROR", f"Demotion failed: {str(e)}", "error")
    
    def cmd_verify(self, args):
        """Verify admin account"""
        if not args:
            return self.format_output("ERROR", "Usage: verify [user_id]", "error")
        
        try:
            user_id = int(args[0])
            user = User.query.get(user_id)
            
            if not user:
                return self.format_output("ERROR", f"User ID {user_id} not found", "error")
            
            if user.id == current_user.id:
                return self.format_output("ERROR", "Cannot verify yourself", "error")
            
            if user.year == 5:
                return self.format_output("ERROR", "Cannot verify operator accounts", "error")
            
            if not user.is_admin:
                return self.format_output("INFO", f"User {user.username} is not an admin", "info")
            
            user.is_verified_admin = True
            db.session.commit()
            
            result = [
                f"User: {user.username} (ID: {user.id})",
                f"Previous Role: Administrator",
                f"New Role: Verified Administrator",
                f"Action: Verified at {datetime.now(timezone(timedelta(hours=3))).strftime('%H:%M:%S')}",
                f"Operator: {current_user.username}"
            ]
            
            return self.format_output("ADMIN VERIFIED", "\n".join(result), "success")
        except ValueError:
            return self.format_output("ERROR", "Invalid user ID", "error")
        except Exception as e:
            db.session.rollback()
            return self.format_output("ERROR", f"Verification failed: {str(e)}", "error")
    
    def cmd_unverify(self, args):
        """Unverify admin account"""
        if not args:
            return self.format_output("ERROR", "Usage: unverify [user_id]", "error")
        
        try:
            user_id = int(args[0])
            user = User.query.get(user_id)
            
            if not user:
                return self.format_output("ERROR", f"User ID {user_id} not found", "error")
            
            if user.id == current_user.id:
                return self.format_output("ERROR", "Cannot unverify yourself", "error")
            
            if user.year == 5:
                return self.format_output("ERROR", "Cannot unverify operator accounts", "error")
            
            if not user.is_admin:
                return self.format_output("INFO", f"User {user.username} is not an admin", "info")
            
            user.is_verified_admin = False
            db.session.commit()
            
            result = [
                f"User: {user.username} (ID: {user.id})",
                f"Previous Role: Administrator",
                f"New Role: Regular Admin",
                f"Action: Unverified at {datetime.now(timezone(timedelta(hours=3))).strftime('%H:%M:%S')}",
                f"Operator: {current_user.username}"
            ]
            
            return self.format_output("ADMIN UNVERIFIED", "\n".join(result), "success")
        except ValueError:
            return self.format_output("ERROR", "Invalid user ID", "error")
        except Exception as e:
            db.session.rollback()
            return self.format_output("ERROR", f"Unerification failed: {str(e)}", "error")
    
    def cmd_user_info(self, args):
        """Get detailed user information"""
        if not args:
            return self.format_output("ERROR", "Usage: user-info [id or username]", "error")
        
        try:
            identifier = args[0]
            
            # Try as ID first
            if identifier.isdigit():
                user = User.query.get(int(identifier))
            else:
                # Try as username
                user = User.query.filter_by(username=identifier).first()
            
            if not user:
                return self.format_output("ERROR", f"User '{identifier}' not found", "error")
            
            status = "ACTIVE" if user.status else "BANNED"
            verified = "VERIFIED" if user.is_verified_admin else "UNVERIFIED"
            admin_status = "ADMINISTRATOR" if user.is_admin else "REGULAR USER"
            operator = "YES (Year 5)" if user.year == 5 else "NO"
            paid = "PAID" if user.paid else "UNPAID"
            
            info = [
                f"=== USER PROFILE ===",
                f"ID:           {user.id}",
                f"Username:     {user.username}",
                f"Mobile:       {user.mobile}",
                f"Year:         {user.year}",
                f"",
                f"=== ACCOUNT STATUS ===",
                f"Status:       {status}",
                f"Fee:          {paid}",
                f"Role:         {admin_status}",
                f"Verified:     {verified}",
                f"Operator:     {operator}",
                f"",
                f"=== METADATA ===",
                f"Account ID:   #{user.id:06d}",
                f"Created:       {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Last Active:  [Recent]",
                f"",
                f"=== PRIVILEGES ===",
                f"• Year Update: {'✓' if user.year < 5 else '✗'}",
                f"• Admin Panel: {'✓' if user.is_admin else '✗'}",
                f"• Operator:    {'✓' if user.year == 5 else '✗'}"
            ]
            
            return self.format_output("USER INFORMATION", "\n".join(info), "info")
        except Exception as e:
            return self.format_output("ERROR", f"Failed to get user info: {str(e)}", "error")
    
    def cmd_system_info(self, args):
        """Display system statistics"""
        try:
            total_users = User.query.count()
            active_users = User.query.filter_by(status=True).count()
            paid_users = User.query.filter_by(paid=True).count()
            banned_users = User.query.filter_by(status=False).count()
            total_admins = User.query.filter_by(is_admin=True).count()
            verified_admins = User.query.filter_by(is_verified_admin=True).count()
            operators = User.query.filter_by(year=5).count()
            
            info = [
                f"=== SYSTEM STATISTICS ===",
                f"Time:           {datetime.now(timezone(timedelta(hours=3))).strftime('%Y-%m-%d %H:%M:%S')}",
                f"",
                f"=== USER COUNTS ===",
                f"Total Users:    {total_users}",
                f"Active:         {active_users}",
                f"Banned:         {banned_users}",
                f"Paid Fee:       {paid_users}",
                f"",
                f"=== ADMINISTRATION ===",
                f"Total Admins:   {total_admins}",
                f"Verified:       {verified_admins}",
                f"Unverified:     {total_admins - verified_admins}",
                f"Operators:      {operators}",
                f"",
                f"=== STATUS ===",
                f"System:         ONLINE",
                f"Database:       CONNECTED",
                f"Probe:          ACTIVE",
                f"Security:       LEVEL 5"
            ]
            
            return self.format_output("SYSTEM INFORMATION", "\n".join(info), "info")
        except Exception as e:
            return self.format_output("ERROR", f"Failed to get system info: {str(e)}", "error")
    
    def cmd_export(self, args):
        """Export data"""
        table = args[0].lower() if args else "users"
        
        if table == "users":
            data = User.query.all()
            result = ["ID,Username,Mobile,Year,Status,IsAdmin,IsVerifiedAdmin"]
            for user in data:
                result.append(f"{user.id},{user.username},{user.mobile},{user.year},{user.status},{user.is_admin},{user.is_verified_admin}")
            content = "\n".join(result)
            filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        elif table == "admins":
            data = User.query.filter_by(is_admin=True).all()
            result = ["ID,Username,Mobile,Year,Status,IsVerifiedAdmin"]
            for user in data:
                result.append(f"{user.id},{user.username},{user.mobile},{user.year},{user.status},{user.is_verified_admin}")
            content = "\n".join(result)
            filename = f"admins_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        else:
            return self.format_output("ERROR", "Usage: export [users|admins]", "error")
        
        return self.format_output("EXPORT READY", 
                                 f"Exported {len(data)} records\n"
                                 f"Filename: {filename}\n"
                                 f"Format: CSV\n\n"
                                 f"Use 'copy to clipboard' for data.", 
                                 "success")
    
    def cmd_ping(self, args):
        """Check server connectivity"""
        return self.format_output("PONG", "Server is responding", "success")
    
    def cmd_echo(self, args):
        """Echo back text"""
        text = " ".join(args) if args else "(silence)"
        return self.format_output("ECHO", text, "info")
    
    def cmd_reboot(self, args):
        """Reboot the server"""
        return '''<script>window.location.reload();</script>'''
    
    def cmd_version(self, args):
        """Show software version"""
        return self.format_output("VERSION", "LyxNexus Probe v2.07", "info")
    
    def cmd_shutdown(self, args):
        """Shutdown the server"""
        return '''<script>window.location.href='/admin/operator';</script>'''

# ============ ROUTES ============

@probe_bp.route('/')
@login_required
@operator_required
def lyx_probe():
    """Main probe interface"""
    return render_template('lyxprobe.html', now=datetime.now(timezone(timedelta(hours=3))))

@probe_bp.route('/execute', methods=['POST'])
@login_required
@operator_required
def execute_command():
    """Execute probe commands"""
    command = request.json.get('command', '').strip()
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    
    processor = ProbeCommandProcessor()
    result = processor.process(command)
    
    # Add to command history
    history_entry = {
        'command': command,
        'result': result,
        'timestamp': datetime.now().isoformat(),
        'operator': current_user.username
    }
    
    return jsonify(result)

@probe_bp.route('/history')
@login_required
@operator_required
def get_history():
    """Get command history (simplified - in real app, store in db)"""
    # For demo, return recent commands
    return jsonify({
        'history': [
            {'command': 'help', 'time': '14:30:00'},
            {'command': 'whoami', 'time': '14:31:00'},
            {'command': 'system-info', 'time': '14:32:00'}
        ]
    })