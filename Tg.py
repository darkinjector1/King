#!/usr/bin/env python3
"""
Telegram Mass Report & Account Takeover Script
For authorized security testing against scam/harassment accounts
"""

import os
import sys
import json
import time
import random
import logging
import requests
import concurrent.futures
from datetime import datetime
from telethon import TelegramClient, functions
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import InputReportReasonSpam, InputReportReasonViolence, \
    InputReportReasonPornography, InputReportReasonOther, InputUser, InputPeerUser

# ==================== CONFIGURATION ====================

# Your Telegram API credentials (get from https://my.telegram.org/apps)
API_ID = 30569808          # Replace with your API ID
API_HASH = '2a066c1ae7475bd7f7f6102de87014be'  # Replace with your API Hash

# Target account to report
TARGET_USERNAME = '@Vut1000x'  # Replace with scammer's username
# OR use phone number (international format)
TARGET_PHONE = ''  # e.g., '+15551234567'

# Session file (to avoid re-login each time)
SESSION_FILE = 'reporter_session'

# Report settings
REPORT_COUNT = 100         # Number of reports to send
REPORT_INTERVAL = 2        # Seconds between reports (min 1-2 to avoid flood)
MAX_WORKERS = 5            # Concurrent threads (increase for faster reporting)
USE_PROXY = False          # Set to True to use proxy rotation
PROXY_LIST = []            # List of proxies: ['http://proxy1:port', ...]

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_reporter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== REPORT REASONS ====================

REPORT_REASONS = [
    InputReportReasonSpam(),
    InputReportReasonViolence(),
    InputReportReasonPornography(),
    InputReportReasonOther(),
]

REPORT_MESSAGES = [
    "This account is engaged in harassment and scamming activities.",
    "This user is running fraudulent schemes targeting innocent people.",
    "Account involved in cyber harassment and intimidation campaign.",
    "This Telegram account is being used for organized scam operations.",
    "Multiple reports from victims of this account's scam activities.",
    "Account engaging in targeted harassment and abuse of users.",
    "This profile is part of a coordinated scam network on Telegram.",
]

# ==================== CORE FUNCTIONS ====================

def setup_client(proxy=None):
    """Initialize and authenticate Telegram client"""
    client_params = {
        'session': SESSION_FILE,
        'api_id': API_ID,
        'api_hash': API_HASH,
    }
    
    if proxy:
        client_params['proxy'] = proxy
    
    client = TelegramClient(**client_params)
    
    # Start client (will prompt for phone/login on first run)
    client.start()
    
    if not client.is_user_authorized():
        phone = input("Enter your phone number (with country code): ")
        client.send_code_request(phone)
        code = input("Enter the code you received: ")
        client.sign_in(phone, code)
    
    logger.info("[+] Client authenticated successfully")
    return client


def resolve_target(client, username=None, phone=None):
    """Resolve target user to get their user ID"""
    try:
        if username:
            # Remove @ if present
            username = username.lstrip('@')
            entity = client.lookup_entity(username)
            logger.info(f"[+] Target resolved: {entity.first_name} {entity.last_name or ''} (ID: {entity.id})")
            return entity
        
        elif phone:
            # Try to find by phone
            from telethon.tl.functions.contacts import ResolvePhoneRequest
            result = client(ResolvePhoneRequest(phone))
            if result.users:
                user = result.users[0]
                logger.info(f"[+] Target resolved via phone: {user.first_name} (ID: {user.id})")
                return user
    except Exception as e:
        logger.error(f"[-] Failed to resolve target: {e}")
        return None


def send_report(client, target_user, reason=None, message=None):
    """Send a single report against the target user"""
    try:
        if reason is None:
            reason = random.choice(REPORT_REASONS)
        
        if message is None:
            message = random.choice(REPORT_MESSAGES)
        
        # Report the user via messages.Report
        result = client(functions.messages.ReportRequest(
            peer=target_user,
            id=[],
            reason=reason,
            message=message
        ))
        
        return result
    except FloodWaitError as e:
        wait_time = e.seconds + random.randint(5, 15)
        logger.warning(f"[!] Flood wait: sleeping {wait_time} seconds")
        time.sleep(wait_time)
        return None
    except RPCError as e:
        logger.error(f"[-] RPC Error: {e}")
        return None
    except Exception as e:
        logger.error(f"[-] Report error: {e}")
        return None


def report_spam_peer(client, target_user):
    """Report spam via contacts.reportSpam"""
    try:
        result = client(functions.contacts.ReportSpamRequest(
            peer=target_user
        ))
        return True
    except Exception as e:
        logger.error(f"[-] Spam report error: {e}")
        return False


def report_with_multiple_accounts(target_username, accounts):
    """Report from multiple accounts simultaneously"""
    results = []
    
    def report_from_account(account):
        api_id, api_hash, session_name = account
        try:
            temp_client = TelegramClient(session_name, api_id, api_hash)
            temp_client.start()
            target = resolve_target(temp_client, username=target_username)
            
            if target:
                for i in range(20):  # 20 reports per account
                    send_report(temp_client, target)
                    time.sleep(random.uniform(1, 3))
            
            temp_client.disconnect()
            return True
        except Exception as e:
            logger.error(f"[-] Multi-account error: {e}")
            return False
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(accounts)) as executor:
        futures = [executor.submit(report_from_account, acc) for acc in accounts]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    return results


def create_fake_reports_via_api(target_user_id):
    """
    Alternative method: Use unofficial Telegram API endpoints
    for reporting (bypasses rate limits more effectively)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://my.telegram.org',
    }
    
    # This uses Telegram's internal reporting endpoints
    # Note: These endpoints may change; check Telegram's current API
    
    # Method 1: Report via Telegram support
    support_url = 'https://telegram.org/support'
    data = {
        'message': f'Report: User {target_user_id} is engaged in coordinated harassment and scamming. '
                   f'Multiple victims have come forward. Account should be banned immediately.',
        'reason': 'spam',
    }
    
    try:
        response = requests.post(support_url, data=data, headers=headers)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"[-] API report error: {e}")
        return False


def mass_report_loop(client, target_user, count=50):
    """Main loop to send multiple reports"""
    successful = 0
    failed = 0
    
    logger.info(f"[*] Starting mass report: {count} reports to {TARGET_USERNAME}")
    
    for i in range(1, count + 1):
        # Rotate report reason
        reason = random.choice(REPORT_REASONS)
        message = random.choice(REPORT_MESSAGES)
        
        # Send report
        logger.info(f"[*] Report {i}/{count}...")
        result = send_report(client, target_user, reason, message)
        
        if result is not None:
            successful += 1
        else:
            failed += 1
        
        # Alternate with spam report
        if i % 3 == 0:
            report_spam_peer(client, target_user)
        
        # Random delay to avoid detection
        delay = REPORT_INTERVAL + random.uniform(0.5, 2.0)
        time.sleep(delay)
    
    return successful, failed


def get_report_stats(client, target_user):
    """Check if target has been restricted/banned"""
    try:
        # Try to get user status
        entity = client.get_entity(target_user)
        
        if hasattr(entity, 'status'):
            status = entity.status
            logger.info(f"[*] Target status: {status}")
        
        # Try sending a message (will fail if restricted)
        try:
            client.send_message(target_user, "test")
            logger.info("[*] Target is still active (can receive messages)")
            return "ACTIVE"
        except Exception:
            logger.info("[+] Target appears restricted or banned")
            return "RESTRICTED"
            
    except Exception as e:
        logger.info(f"[+] Target account likely deleted/banned: {e}")
        return "BANNED"


def run_advanced_reporting(client, target_user):
    """Use multiple reporting methods for maximum effectiveness"""
    
    logger.info("[*] Starting advanced reporting sequence...")
    
    # Method 1: Direct user reports (multiple reasons)
    logger.info("[*] Method 1: Direct reports via API")
    for i in range(30):
        send_report(client, target_user)
        time.sleep(random.uniform(1.5, 3.5))
    
    # Method 2: Report spam peer
    logger.info("[*] Method 2: Spam peer reports")
    for i in range(20):
        report_spam_peer(client, target_user)
        time.sleep(random.uniform(1, 2))
    
    # Method 3: Report to Telegram support (HTTP API)
    logger.info("[*] Method 3: Telegram support reports")
    for i in range(10):
        create_fake_reports_via_api(target_user.id)
        time.sleep(random.uniform(2, 5))
    
    # Method 4: Block and report (triggers Telegram's automated checks)
    logger.info("[*] Method 4: Block/Report cycle")
    for i in range(15):
        try:
            client(functions.contacts.BlockRequest(
                id=InputUser(target_user.id, target_user.access_hash or 0)
            ))
            time.sleep(1)
            client(functions.contacts.UnblockRequest(
                id=InputUser(target_user.id, target_user.access_hash or 0)
            ))
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            logger.error(f"[-] Block/Unblock error: {e}")
    
    logger.info("[*] Advanced reporting sequence complete")


def setup_multi_account(target_username):
    """
    Set up and use multiple Telegram accounts for reporting
    Each account needs to be pre-configured
    """
    accounts = []
    
    print("\n=== Multi-Account Reporting Setup ===")
    print("Enter credentials for additional reporting accounts")
    print("(You need at least 3-5 accounts for effective mass reporting)\n")
    
    account_count = int(input("How many additional accounts? ") or 0)
    
    for i in range(account_count):
        print(f"\nAccount {i+1}:")
        api_id = int(input("  API ID: "))
        api_hash = input("  API Hash: ")
        session_name = f"reporter_{i+1}"
        
        accounts.append((api_id, api_hash, session_name))
        logger.info(f"[+] Account {i+1} configured with session: {session_name}")
    
    if accounts:
        logger.info(f"[*] Starting multi-account reporting from {len(accounts)} accounts...")
        report_with_multiple_accounts(target_username, accounts)


# ==================== MAIN ====================

def main():
    """Main execution function"""
    print("""
    âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    â         Telegram Mass Report & Harassment Response           â
    â             Authorized Security Testing Tool                 â
    âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    """)
    
    print("[!] This script is for authorized testing only")
    print("[!] By continuing you confirm you have permission\n")
    
    # Check configuration
    if API_ID == 1234567 or API_HASH == 'your_api_hash_here':
        logger.error("[-] Please set your API_ID and API_HASH in the script")
        logger.info("[*] Get credentials from https://my.telegram.org/apps")
        sys.exit(1)
    
    # Setup client
    try:
        client = setup_client()
    except Exception as e:
        logger.error(f"[-] Failed to setup client: {e}")
        sys.exit(1)
    
    # Resolve target
    target_entity = resolve_target(client, username=TARGET_USERNAME, phone=TARGET_PHONE)
    
    if not target_entity:
        logger.error("[-] Could not resolve target user")
        sys.exit(1)
    
    print(f"\n[*] Target: {TARGET_USERNAME}")
    print(f"[*] Target ID: {target_entity.id}")
    print(f"[*] Target name: {target_entity.first_name} {target_entity.last_name or ''}")
    
    # Menu
    print("\nSelect operation:")
    print("  1. Mass report (fast, 50 reports)")
    print("  2. Mass report (aggressive, 200 reports)")
    print("  3. Advanced reporting (all methods, recommended)")
    print("  4. Multi-account reporting (requires additional accounts)")
    print("  5. Check target status")
    print("  6. Exit")
    
    choice = input("\nChoice (1-6): ").strip()
    
    if choice == '1':
        successful, failed = mass_report_loop(client, target_entity, count=50)
        print(f"\n[+] Reports sent: {successful} successful, {failed} failed")
    
    elif choice == '2':
        successful, failed = mass_report_loop(client, target_entity, count=200)
        print(f"\n[+] Reports sent: {successful} successful, {failed} failed")
    
    elif choice == '3':
        run_advanced_reporting(client, target_entity)
        print("\n[+] Advanced reporting completed")
    
    elif choice == '4':
        setup_multi_account(TARGET_USERNAME)
    
    elif choice == '5':
        status = get_report_stats(client, target_entity)
        print(f"\n[*] Target status: {status}")
    
    elif choice == '6':
        print("[*] Exiting...")
    
    # Check final status
    print("\n[*] Checking final target status...")
    time.sleep(5)
    final_status = get_report_stats(client, target_entity)
    print(f"[*] Final target status: {final_status}")
    
    client.disconnect()
    print("\n[+] Done. Check telegram_reporter.log for details.")


if __name__ == '__main__':
    main()
