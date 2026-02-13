#!/usr/bin/env python3
"""
Terminal-based Rate Limiter Tester
Run this to test if your rate limiter is working
"""

import requests
import time
import sys
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import random

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
BOLD = '\033[1m'
END = '\033[0m'

class RateLimiterTester:
    def __init__(self, target_url="http://127.0.0.1:5000"):
        self.target_url = target_url
        self.total_requests = 0
        self.blocked = 0
        self.success = 0
        self.errors = 0
        
    def print_banner(self):
        print(f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════╗
║     RATE LIMITER TERMINAL TEST SUITE                    ║
║     Testing: {self.target_url:<35} ║
╚══════════════════════════════════════════════════════════╝{END}
        """)

    def test_basic_rate_limit(self, num_requests=100):
        """Test 1: Basic rate limiting with rapid requests"""
        print(f"\n{BLUE}{BOLD}[TEST 1] Basic Rate Limiting{END}")
        print(f"Sending {num_requests} rapid requests to {self.target_url}")
        print("-" * 60)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0'
        }
        
        for i in range(num_requests):
            # Rotate through common vulnerable endpoints
            endpoints = [
                '/.env',
                '/api/user/',
                '/_internal/api/setup.php',
                '/admin',
                '/config',
                '/wp-admin',
                '/backup.zip',
                '/.git/config'
            ]
            endpoint = random.choice(endpoints)
            
            try:
                response = requests.get(
                    f"{self.target_url}{endpoint}",
                    headers=headers,
                    timeout=5  # Increased timeout for slow servers
                )
                
                self.total_requests += 1
                
                if response.status_code == 429:
                    self.blocked += 1
                    print(f"{RED}⛔ {i+1:3d}: BLOCKED (429) - {endpoint}{END}")
                else:
                    self.success += 1
                    status_color = GREEN if response.status_code == 404 else YELLOW
                    print(f"{status_color}✅ {i+1:3d}: {response.status_code} - {endpoint}{END}")
                    
            except requests.exceptions.ConnectionError:
                self.errors += 1
                self.total_requests += 1
                print(f"{RED}❌ {i+1:3d}: Connection refused - Server might be down?{END}")
            except requests.exceptions.Timeout:
                self.errors += 1
                self.total_requests += 1
                print(f"{YELLOW}⏰ {i+1:3d}: Timeout - Server slow{END}")
            except Exception as e:
                self.errors += 1
                self.total_requests += 1
                print(f"{RED}❌ {i+1:3d}: Error - {str(e)[:50]}{END}")
            
            # No delay - rapid fire!
            time.sleep(0.1)  # Slightly increased delay to avoid overwhelming
        
        self.print_results("Basic Test")

    def test_concurrent_attacks(self, threads=5, requests_per_thread=20):
        """Test 2: Simulate multiple attackers simultaneously"""
        print(f"\n{BLUE}{BOLD}[TEST 2] Concurrent Attack Simulation{END}")
        print(f"Starting {threads} threads, {requests_per_thread} requests each")
        print("-" * 60)
        
        def attacker(thread_id):
            local_blocked = 0
            local_success = 0
            local_total = 0
            
            # Different user agents for each thread
            user_agents = [
                f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/{random.randint(120, 135)}.0.0.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64) Firefox/91.0',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
                'curl/7.68.0'
            ]
            
            for i in range(requests_per_thread):
                endpoint = random.choice([
                    '/.env',
                    '/api/user/',
                    '/_internal/api/setup.php?action=exists',
                    '/admin/',
                    '/config'
                ])
                
                headers = {'User-Agent': random.choice(user_agents)}
                
                try:
                    response = requests.get(
                        f"{self.target_url}{endpoint}",
                        headers=headers,
                        timeout=3
                    )
                    
                    local_total += 1
                    
                    if response.status_code == 429:
                        local_blocked += 1
                        print(f"{RED}[Thread-{thread_id}] ⛔ Blocked{END}")
                    else:
                        local_success += 1
                        
                except Exception:
                    local_total += 1
                    pass
            
            return local_blocked, local_success, local_total
        
        # Run threads
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(attacker, i) for i in range(threads)]
            
            for future in futures:
                b, s, t = future.result()
                self.blocked += b
                self.success += s
                self.total_requests += t
        
        self.print_results("Concurrent Test")

    def test_script_kiddie_simulator(self):
        """Test 3: Simulate our Chrome 134 friend"""
        print(f"\n{BLUE}{BOLD}[TEST 3] Script Kiddie Simulator (Chrome 134 Edition){END}")
        print("-" * 60)
        
        # Their exact user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        }
        
        # Common PHP scanner wordlist
        wordlist = [
            '/.env',
            '/_internal/api/setup.php?action=exists',
            '/api/user/',
            '/admin/',
            '/wp-admin',
            '/phpmyadmin',
            '/config.php',
            '/backup.sql',
            '/.git/config',
            '/vendor/phpunit/src/Util/PHP/eval-stdin.php',
            '/laravel/.env',
            '/wordpress/wp-config.php',
            '/dump.sql',
            '/database.sql',
            '/.aws/credentials'
        ]
        
        print(f"{YELLOW}Simulating automated scanner with Chrome 134...{END}\n")
        
        for i, path in enumerate(wordlist * 2):  # Loop through twice
            try:
                print(f"🔍 Probing: {path:<40}", end=' ')
                sys.stdout.flush()
                
                response = requests.get(
                    f"{self.target_url}{path}",
                    headers=headers,
                    timeout=3
                )
                
                self.total_requests += 1
                
                if response.status_code == 429:
                    self.blocked += 1
                    print(f"{RED}⛔ RATE LIMITED!{END}")
                elif response.status_code == 404:
                    self.success += 1
                    print(f"{GREEN}📄 404 Not Found{END}")
                else:
                    self.success += 1
                    print(f"{YELLOW}⚠️ Got {response.status_code}{END}")
                    
            except Exception as e:
                self.errors += 1
                self.total_requests += 1
                print(f"{RED}❌ Error{END}")
            
            # Script kiddies scan fast but not instant
            time.sleep(0.2)
        
        self.print_results("Script Kiddie Test")

    def test_evasion_techniques(self):
        """Test 4: Try to bypass rate limiter"""
        print(f"\n{BLUE}{BOLD}[TEST 4] Evasion Technique Testing{END}")
        print("-" * 60)
        
        techniques = [
            ("IP Spoofing", {'X-Forwarded-For': f'192.168.{random.randint(1,255)}.{random.randint(1,255)}'}),
            ("Referer Spoofing", {'Referer': 'https://google.com'}),
            ("Random User-Agents", {'User-Agent': f'Browser/{random.randint(1,100)}'}),
            ("Accept Randomization", {'Accept': random.choice(['text/html', 'application/json', '*/*'])}),
            ("All Headers", {
                'User-Agent': random.choice(['Chrome/131', 'Firefox/91', 'Safari/605']),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
        ]
        
        for tech_name, headers in techniques:
            print(f"\n{YELLOW}Testing: {tech_name}{END}")
            blocked = 0
            tech_total = 0
            
            for i in range(20):
                try:
                    response = requests.get(
                        f"{self.target_url}/.env",
                        headers=headers,
                        timeout=3
                    )
                    
                    tech_total += 1
                    
                    if response.status_code == 429:
                        blocked += 1
                        print(f"  {RED}⛔ Request {i+1:2d}: Blocked{END}")
                    else:
                        print(f"  {GREEN}✅ Request {i+1:2d}: {response.status_code}{END}")
                        
                except Exception:
                    tech_total += 1
                    pass
            
            self.total_requests += tech_total
            self.blocked += blocked
            self.success += (tech_total - blocked)
            
            if blocked > 15:
                print(f"  {GREEN}✓ Rate limiter caught evasion{END}")
            elif blocked > 0:
                print(f"  {YELLOW}⚠ Partial blocking{END}")
            else:
                print(f"  {RED}✗ No blocks - evasion possible{END}")

    def print_results(self, test_name):
        """Print colored results"""
        print(f"\n{CYAN}{BOLD}📊 {test_name} Results:{END}")
        print(f"  Total Requests: {self.total_requests}")
        print(f"  {GREEN}✅ Success: {self.success}{END}")
        print(f"  {RED}⛔ Blocked: {self.blocked}{END}")
        print(f"  {YELLOW}⚠️ Errors: {self.errors}{END}")
        
        if self.total_requests > 0 and self.blocked > 0:
            block_rate = (self.blocked / self.total_requests) * 100
            print(f"\n  {GREEN}✓ Rate limiter IS working (Block rate: {block_rate:.1f}%){END}")
        elif self.total_requests > 0 and self.blocked == 0:
            print(f"\n  {RED}✗ Rate limiter NOT working (No blocks detected){END}")

    def run_full_audit(self):
        """Run all tests"""
        self.print_banner()
        
        # Reset counters
        self.total_requests = 0
        self.blocked = 0
        self.success = 0
        self.errors = 0
        
        # Check if server is reachable
        try:
            print(f"Checking connection to {self.target_url}...")
            response = requests.get(self.target_url, timeout=5)
            print(f"{GREEN}✓ Server is reachable (Status: {response.status_code}){END}\n")
        except requests.exceptions.ConnectionError:
            print(f"{RED}✗ Cannot connect to {self.target_url}{END}")
            print(f"{YELLOW}Make sure your server is running and the URL is correct!{END}")
            return
        except Exception as e:
            print(f"{YELLOW}⚠ Warning: Server check failed - {str(e)}{END}")
            print(f"{YELLOW}Continuing anyway...{END}\n")
        
        # Run tests
        input(f"{CYAN}Press Enter to start Test 1 (Basic Rate Limiting)...{END}")
        self.test_basic_rate_limit(num_requests=50)  # Reduced to 50 for Render.com
        
        input(f"\n{CYAN}Press Enter to start Test 2 (Concurrent Attacks)...{END}")
        self.test_concurrent_attacks(threads=3, requests_per_thread=10)  # Reduced
        
        input(f"\n{CYAN}Press Enter to start Test 3 (Script Kiddie Simulator)...{END}")
        self.test_script_kiddie_simulator()
        
        input(f"\n{CYAN}Press Enter to start Test 4 (Evasion Techniques)...{END}")
        self.test_evasion_techniques()
        
        # Final summary
        print(f"\n{BOLD}{CYAN}{'='*60}{END}")
        print(f"{BOLD}{CYAN}FINAL AUDIT SUMMARY{END}")
        print(f"{CYAN}{'='*60}{END}")
        print(f"Target URL: {self.target_url}")
        print(f"Total Requests: {self.total_requests}")
        print(f"{GREEN}Successful (Not Blocked): {self.success}{END}")
        print(f"{RED}Blocked by Rate Limiter: {self.blocked}{END}")
        print(f"{YELLOW}Errors: {self.errors}{END}")
        
        if self.total_requests > 0:
            block_rate = (self.blocked / self.total_requests) * 100
            
            if self.blocked > 0:
                print(f"\n{GREEN}{BOLD}✅ RATE LIMITER IS WORKING!{END}")
                print(f"   Block rate: {block_rate:.1f}%")
                
                if block_rate > 50:
                    print(f"   {GREEN}Excellent - Strong rate limiting{END}")
                elif block_rate > 20:
                    print(f"   {GREEN}Good - Rate limiter active{END}")
                elif block_rate > 0:
                    print(f"   {YELLOW}Fair - Could be stricter{END}")
            else:
                print(f"\n{RED}{BOLD}❌ RATE LIMITER IS NOT WORKING!{END}")
                print(f"   {YELLOW}Check your Flask-Limiter configuration{END}")
                print(f"\n{YELLOW}Recommendations:{END}")
                print(f"   1. Install flask-limiter: pip install flask-limiter")
                print(f"   2. Add rate limiting to your app")
                print(f"   3. Use Redis for production")
        else:
            print(f"\n{RED}No requests were completed successfully{END}")

def main():
    """Main entry point"""
    # Parse command line arguments
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "https://lyxnexus.onrender.com"  # Default to your site
    
    # Create and run tester
    tester = RateLimiterTester(target)
    
    try:
        tester.run_full_audit()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{END}")
        sys.exit(1)

if __name__ == "__main__":
    main()