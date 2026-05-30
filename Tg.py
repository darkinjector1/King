#!/usr/bin/env python3
"""
Telegram Mass Report & Account Takeover Script (FIXED VERSION)
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

# ==================== কনফিগারেশন ====================

# আপনার টেলিগ্রাম API credentials (https://my.telegram.org/apps থেকে নিন)
API_ID = 30569808          # আপনার API ID
API_HASH = '2a066c1ae7475bd7f7f6102de87014be'  # আপনার API Hash

# টার্গেট অ্যাকাউন্ট
TARGET_USERNAME = '@Vut1000x'  # স্ক্যামারের ইউজারনেম
TARGET_PHONE = ''  # ফোন নাম্বার (ঐচ্ছিক)

# সেশন ফাইল
SESSION_FILE = 'reporter_session'

# রিপোর্ট সেটিংস
REPORT_COUNT = 50         # কতগুলো রিপোর্ট পাঠাবে
REPORT_INTERVAL = 3       # প্রতি রিপোর্টের মধ্যে সময় (সেকেন্ড)
MAX_WORKERS = 3           # কনকারেন্ট থ্রেড
USE_PROXY = False
PROXY_LIST = []

# বাগ ফিক্স: সঠিক লগিং কনফিগারেশন
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_reporter.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== রিপোর্ট রিজনস ====================

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

# ==================== কোর ফাংশনস ====================

def setup_client(proxy=None):
    """Initialize and authenticate Telegram client"""
    client_params = {
        'session': SESSION_FILE,
        'api_id': API_ID,
        'api_hash': API_HASH,
        'request_retries': 5,  # রিট্রাই যোগ করা হলো
        'connection_retries': 5,
        'retry_delay': 2,
    }
    
    if proxy:
        client_params['proxy'] = proxy
    
    client = TelegramClient(**client_params)
    
    # কানেক্ট করার চেষ্টা
    try:
        client.connect()
    except Exception as e:
        logger.error(f"[-] Connection error: {e}")
        # যদি সেশন ফাইল নষ্ট হয়ে যায় তাহলে ডিলিট করে আবার চেষ্টা
        if os.path.exists(f"{SESSION_FILE}.session"):
            os.remove(f"{SESSION_FILE}.session")
            logger.info("[*] Removed corrupted session file. Try again.")
        sys.exit(1)
    
    # লগইন চেক
    if not client.is_user_authorized():
        phone = input("Enter your phone number (with country code): ")
        try:
            client.send_code_request(phone)
            code = input("Enter the code you received: ")
            client.sign_in(phone, code)
        except Exception as e:
            logger.error(f"[-] Login error: {e}")
            sys.exit(1)
    
    logger.info("[+] Client authenticated successfully")
    return client


def resolve_target(client, username=None, phone=None):
    """Resolve target user to get their user ID"""
    try:
        if username:
            # @ রিমুভ করে নিন
            username = username.lstrip('@')
            # Try to get entity by username
            entity = client.get_entity(username)
            logger.info(f"[+] Target resolved: {entity.first_name or ''} {entity.last_name or ''} (ID: {entity.id})")
            return entity
        
        elif phone:
            # ফোন দিয়ে খোঁজা
            from telethon.tl.functions.contacts import ResolvePhoneRequest
            result = client(ResolvePhoneRequest(phone))
            if result.users:
                user = result.users[0]
                logger.info(f"[+] Target resolved via phone: {user.first_name or ''} (ID: {user.id})")
                return user
    except ValueError as e:
        # ইউজার না থাকলে
        logger.error(f"[-] Target not found: {e}")
        return None
    except Exception as e:
        logger.error(f"[-] Failed to resolve target: {e}")
        return None
    
    return None


def send_report(client, target_user, reason=None, message=None):
    """Send a single report against the target user"""
    try:
        if reason is None:
            reason = random.choice(REPORT_REASONS)
        
        if message is None:
            message = random.choice(REPORT_MESSAGES)
        
        # বাগ ফিক্স: সঠিক প্যারামিটার সহ Report
        result = client(functions.messages.ReportRequest(
            peer=target_user,  # সরাসরি entity দিন
            id=[],  # খালি লিস্ট দিন (পুরো ইউজার রিপোর্ট)
            reason=reason,
            message=message
        ))
        
        return result
        
    except FloodWaitError as e:
        wait_time = e.seconds + random.randint(5, 15)
        logger.warning(f"[!] Flood wait: sleeping {wait_time} seconds")
        time.sleep(wait_time)
        return True  # ভুল ছিল None রিটার্ন, এখন True
    
    except RPCError as e:
        logger.error(f"[-] RPC Error: {e}")
        time.sleep(10)  # একটু অপেক্ষা
        return False
    
    except Exception as e:
        logger.error(f"[-] Report error: {e}")
        return False


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


def mass_report_loop(client, target_user, count=50):
    """Main loop to send multiple reports"""
    successful = 0
    failed = 0
    
    logger.info(f"[*] Starting mass report: {count} reports to {TARGET_USERNAME}")
    
    for i in range(1, count + 1):
        # রোটেট রিপোর্ট রিজন
        reason = random.choice(REPORT_REASONS)
        message = random.choice(REPORT_MESSAGES)
        
        # Send report
        logger.info(f"[*] Report {i}/{count}...")
        result = send_report(client, target_user, reason, message)
        
        if result is not False:  # বাগ ফিক্স: True/False চেক
            successful += 1
        else:
            failed += 1
        
        # প্রতি ৩ রিপোর্টে একবার স্প্যাম রিপোর্ট
        if i % 3 == 0:
            report_spam_peer(client, target_user)
        
        # Delay
        delay = REPORT_INTERVAL + random.uniform(0.5, 2.0)
        time.sleep(delay)
    
    return successful, failed


def get_report_stats(client, target_user):
    """Check if target has been restricted/banned"""
    try:
        # ইউজার এখনো এক্সিস্ট কিনা চেক
        try:
            entity = client.get_entity(target_user)
            
            # মেসেজ পাঠানোর চেষ্টা
            try:
                client.send_message(entity, "Hello")
                logger.info("[*] Target is still active")
                return "ACTIVE"
            except Exception:
                logger.info("[+] Target appears restricted or banned")
                return "RESTRICTED"
                
        except ValueError:
            logger.info("[+] Target account not found - likely banned!")
            return "BANNED"
        
    except Exception as e:
        logger.info(f"[+] Target account deleted/banned: {e}")
        return "BANNED"


def run_advanced_reporting(client, target_user):
    """Use multiple reporting methods for maximum effectiveness"""
    
    logger.info("[*] Starting advanced reporting sequence...")
    
    # Method 1: Direct user reports
    logger.info("[*] Method 1: Direct reports")
    for i in range(30):
        send_report(client, target_user)
        time.sleep(random.uniform(1.5, 3.5))
    
    # Method 2: Report spam peer
    logger.info("[*] Method 2: Spam peer reports")
    for i in range(20):
        report_spam_peer(client, target_user)
        time.sleep(random.uniform(1, 2))
    
    # Method 3: Block and report cycle
    logger.info("[*] Method 3: Block/Report cycle")
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


def check_config():
    """কনফিগারেশন চেক"""
    if API_ID == 1234567 or API_HASH == 'your_api_hash_here':
        logger.error("[-] Please set your API_ID and API_HASH in the script")
        logger.info("[*] Get credentials from https://my.telegram.org/apps")
        return False
    
    if TARGET_USERNAME == '@scammer_username' and TARGET_PHONE == '':
        logger.error("[-] Please set your TARGET_USERNAME in the script")
        return False
    
    return True


# ==================== মেইন ====================

def main():
    """Main execution function"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         Telegram Mass Report & Harassment Response       ║
    ║             Authorized Security Testing Tool             ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    print("[!] This script is for authorized testing only")
    print("[!] By continuing you confirm you have permission\n")
    
    # কনফিগ চেক
    if not check_config():
        sys.exit(1)
    
    # সেটআপ ক্লায়েন্ট
    try:
        client = setup_client()
    except Exception as e:
        logger.error(f"[-] Failed to setup client: {e}")
        sys.exit(1)
    
    # টার্গেট রেজল্ভ
    target_entity = resolve_target(client, username=TARGET_USERNAME, phone=TARGET_PHONE)
    
    if not target_entity:
        logger.error("[-] Could not resolve target user")
        client.disconnect()
        sys.exit(1)
    
    print(f"\n[*] Target: {TARGET_USERNAME}")
    print(f"[*] Target ID: {target_entity.id}")
    print(f"[*] Target name: {target_entity.first_name or ''} {target_entity.last_name or ''}")
    
    # মেনু
    print("\nSelect operation:")
    print("  1. Mass report (fast, 50 reports)")
    print("  2. Mass report (aggressive, 200 reports)")
    print("  3. Advanced reporting (all methods, recommended)")
    print("  4. Check target status")
    print("  5. Exit")
    
    choice = input("\nChoice (1-5): ").strip()
    
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
        status = get_report_stats(client, target_entity)
        print(f"\n[*] Target status: {status}")
    
    elif choice == '5':
        print("[*] Exiting...")
    
    # ফাইনাল স্ট্যাটাস চেক
    if choice in ['1', '2', '3']:
        print("\n[*] Checking final target status...")
        time.sleep(10)
        final_status = get_report_stats(client, target_entity)
        print(f"[*] Final target status: {final_status}")
    
    client.disconnect()
    print("\n[+] Done. Check telegram_reporter.log for details.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[-] Fatal error: {e}")
        sys.exit(1)
