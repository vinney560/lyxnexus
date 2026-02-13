#!/usr/bin/env python3
"""
/api/announcements Data Fetcher
Tests if announcements can be accessed without proper auth
"""

import requests
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor

# Configuration
URL = "https://lyxnexus.onrender.com/api/users"
TOTAL_REQUESTS = 100
CONCURRENT_THREADS = 10

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

# Different user agents to try
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15',
    'curl/7.68.0',
    'Mozilla/5.0 (compatible; Googlebot/2.1)',
    'PostmanRuntime/7.26.8'
]

# Different auth headers to try
AUTH_HEADERS = [
    {},
    {'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ'},
    {'Authorization': 'Basic YWRtaW46YWRtaW4='},
    {'Authorization': 'Token 1234567890'},
    {'X-API-Key': '1234567890'},
    {'X-Admin': 'true'},
    {'Cookie': 'session=admin123'},
    {'Authorization': 'Bearer admin123'},
]

# Different content types
CONTENT_TYPES = [
    {'Accept': 'application/json'},
    {'Accept': 'text/html'},
    {'Accept': '*/*'},
    {'Accept': 'application/xml'},
]

# Global counters
success_count = 0
blocked_count = 0
error_count = 0
data_found = False
status_codes = {}

def fetch_announcements(thread_id, request_num):
    """Try to fetch announcements"""
    global success_count, blocked_count, error_count, data_found
    
    # Randomize headers
    headers = {
        'User-Agent': USER_AGENTS[request_num % len(USER_AGENTS)],
        **CONTENT_TYPES[request_num % len(CONTENT_TYPES)]
    }
    
    # Add random auth header 50% of the time
    if request_num % 2 == 0:
        headers.update(AUTH_HEADERS[request_num % len(AUTH_HEADERS)])
    
    # Try different HTTP methods
    methods = ['GET', 'POST', 'OPTIONS', 'HEAD']
    method = methods[request_num % len(methods)]
    
    try:
        if method == 'GET':
            response = requests.get(URL, headers=headers, timeout=3)
        elif method == 'POST':
            response = requests.post(URL, headers=headers, json={'test': True}, timeout=3)
        elif method == 'OPTIONS':
            response = requests.options(URL, headers=headers, timeout=3)
        else:  # HEAD
            response = requests.head(URL, headers=headers, timeout=3)
        
        # Track status codes
        status_codes[response.status_code] = status_codes.get(response.status_code, 0) + 1
        
        if response.status_code == 429:
            blocked_count += 1
            print(f"{RED}[Thread {thread_id}] ⛔ RATE LIMITED (429) - {method}{END}")
            
        elif response.status_code == 403:
            print(f"{YELLOW}[Thread {thread_id}] 🔒 FORBIDDEN (403) - Need auth{END}")
            success_count += 1
            
        elif response.status_code == 401:
            print(f"{YELLOW}[Thread {thread_id}] 🔑 UNAUTHORIZED (401) - Need login{END}")
            success_count += 1
            
        elif response.status_code == 404:
            print(f"{BLUE}[Thread {thread_id}] 🔍 NOT FOUND (404) - Endpoint doesn't exist{END}")
            success_count += 1
            
        elif response.status_code == 200:
            success_count += 1
            data_found = True
            
            # Try to parse JSON
            try:
                data = response.json()
                data_preview = str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
                print(f"{GREEN}[Thread {thread_id}] 🎉 SUCCESS! Data retrieved:{END}")
                print(f"{GREEN}    {data_preview}{END}")
                
                # If it's announcements, print them!
                if isinstance(data, list):
                    print(f"{GREEN}    Found {len(data)} announcements!{END}")
                    for i, item in enumerate(data[:3]):  # Show first 3
                        print(f"    {i+1}. {item.get('title', 'No title')}")
                elif isinstance(data, dict):
                    print(f"{GREEN}    Keys: {list(data.keys())}{END}")
                    
            except:
                print(f"{GREEN}[Thread {thread_id}] ✅ Success (200) - Response: {response.text[:100]}{END}")
        else:
            error_count += 1
            print(f"{RED}[Thread {thread_id}] ❌ Unknown status: {response.status_code}{END}")
            
    except requests.exceptions.ConnectionError:
        error_count += 1
        print(f"{RED}[Thread {thread_id}] ❌ Connection refused{END}")
    except requests.exceptions.Timeout:
        error_count += 1
        print(f"{RED}[Thread {thread_id}] ⏰ Timeout{END}")
    except Exception as e:
        error_count += 1
        print(f"{RED}[Thread {thread_id}] ❌ Error: {str(e)[:50]}{END}")

def worker(thread_id):
    """Thread worker"""
    for i in range(TOTAL_REQUESTS // CONCURRENT_THREADS):
        fetch_announcements(thread_id, i)
        time.sleep(0.05)  # Small delay

def main():
    global success_count, blocked_count, error_count, data_found, status_codes
    
    print(f"{BLUE}{'='*60}{END}")
    print(f"{BLUE}🔍 TESTING /api/announcements ACCESS{END}")
    print(f"{BLUE}{'='*60}{END}")
    print(f"URL: {URL}")
    print(f"Requests: {TOTAL_REQUESTS}")
    print(f"Threads: {CONCURRENT_THREADS}")
    print(f"{BLUE}{'='*60}{END}\n")
    
    start_time = time.time()
    
    # Run threads
    with ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        futures = [executor.submit(worker, i) for i in range(CONCURRENT_THREADS)]
        for future in futures:
            future.result()
    
    elapsed = time.time() - start_time
    
    # Results
    print(f"\n{BLUE}{'='*60}{END}")
    print(f"{BLUE}📊 RESULTS - /api/announcements{END}")
    print(f"{BLUE}{'='*60}{END}")
    print(f"Total Requests: {TOTAL_REQUESTS}")
    print(f"Time: {elapsed:.2f} seconds")
    print(f"Requests/sec: {TOTAL_REQUESTS/elapsed:.1f}")
    print(f"\nStatus Codes:")
    
    for code, count in sorted(status_codes.items()):
        if code == 200:
            color = GREEN
        elif code == 429:
            color = RED
        elif code in [401, 403]:
            color = YELLOW
        elif code == 404:
            color = BLUE
        else:
            color = END
        print(f"  {color}HTTP {code}: {count}{END}")
    
    print(f"\n{BLUE}Summary:{END}")
    print(f"  {GREEN}✅ Success (non-blocked): {success_count}{END}")
    print(f"  {RED}⛔ Blocked (429): {blocked_count}{END}")
    print(f"  {RED}❌ Errors: {error_count}{END}")
    
    if data_found:
        print(f"\n{GREEN}{'⚠️'*60}{END}")
        print(f"{GREEN}⚠️  WARNING: SUCCESSFULLY RETRIEVED ANNOUNCEMENTS DATA!{END}")
        print(f"{GREEN}⚠️  /api/users may be publicly accessible!{END}")
        print(f"{GREEN}{'⚠️'*60}{END}")
    elif 404 in status_codes:
        print(f"\n{BLUE}🔍 Endpoint /api/users not found (404){END}")
    elif 403 in status_codes or 401 in status_codes:
        print(f"\n{GREEN}✅ Endpoint requires authentication - SECURE!{END}")
    elif 429 in status_codes:
        print(f"\n{GREEN}✅ Rate limiting active on this endpoint{END}")
    else:
        print(f"\n{YELLOW}⚠️  Mixed results - investigate further{END}")

if __name__ == "__main__":
    main()