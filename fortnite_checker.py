# fortnite_bot.py – FULL FORTNITE SKIN CHECKER / LOCKER BOT (PERFECTED)
import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
import base64
import random
import secrets
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# ------------------- CONFIG -------------------
TOKEN = "MTMyODIwNzkyMTUwNjY4MDg5NA.GiAQPM.epj5TKT6h4cc56HU07GSiULBQ0MQsHhx5-UvHQ"
CLIENT_ID = "34a02cf8f4414e29b15921876da36f9a"
CLIENT_SECRET = "daafbccc737745039dffe53d94fc76cf"
FREE_ROLE = "Stock User"
PAID_ROLE = "Premium User"
ADMIN_ROLE = "Admin"

# PUBLIC VERCEL URL (DEPLOY THIS: https://vercel.com/new/clone?repo-url=https://github.com/groksupport/fortnite-oauth-redirect)
REDIRECT_URI = "https://your-vercel-site.vercel.app"  # REPLACE WITH YOUR URL
# ------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- PATHS ----------
USERS_DIR = Path("users")
USERS_DIR.mkdir(exist_ok=True)

def user_path(uid: int) -> Path:
    return USERS_DIR / f"{uid}.json"

# ---------- STOCK ----------
def stock_paths(name: str):
    return Path(f"stock_{name}.txt"), Path(f"used_{name}.txt")

def load_stock(name: str) -> List[str]:
    stock_file, used_file = stock_paths(name)
    if not stock_file.exists():
        return []
    lines = [l.strip() for l in stock_file.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip() and ":" in l]
    used = set()
    if used_file.exists():
        used = {l.strip() for l in used_file.read_text(encoding="utf-8", errors="ignore").splitlines()}
    return [l for l in lines if l not in used]

def mark_used(name: str, line: str):
    _, used_file = stock_paths(name)
    used_file.write_text(used_file.read_text(encoding="utf-8", errors="ignore") + line + "\n", encoding="utf-8")

# ---------- AUTH ----------
def basic_auth() -> str:
    return f"Basic {base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()}"

# ---------- USER SESSION ----------
def load_user(uid: int) -> Dict[str, Any] | None:
    p = user_path(uid)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if "expires_at" in data:
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return data
    except Exception as e:
        print(f"[ERROR] Failed to load user {uid}: {e}")
        return None

def save_user(uid: int, data: Dict[str, Any]):
    data = data.copy()
    if "expires_at" in data:
        data["expires_at"] = data["expires_at"].isoformat()
    user_path(uid).write_text(json.dumps(data, indent=2), encoding="utf-8")

# ---------- PROFILE & COSMETICS ----------
async def fetch_profile(http: aiohttp.ClientSession, account_id: str, token: str) -> Dict[str, Any]:
    url = f"https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{account_id}/client/QueryProfile?profileId=athena"
    async with http.post(url, headers={"Authorization": f"bearer {token}"}, json={}) as r:
        if r.status != 200:
            raise Exception(f"Profile error {r.status}")
        return await r.json()

async def get_cosmetic(http: aiohttp.ClientSession, cid: str) -> Dict[str, Any] | None:
    async with http.get(f"https://fortnite-api.com/v2/cosmetics/br/{cid.lower()}") as r:
        if r.status == 200:
            return (await r.json())["data"]
        return None

# ---------- TOKEN REFRESH ----------
@tasks.loop(minutes=30)
async def token_refresh():
    now = datetime.now(timezone.utc)
    async with aiohttp.ClientSession() as http:
        for file in USERS_DIR.glob("*.json"):
            uid = int(file.stem)
            sess = load_user(uid)
            if not sess or now < sess["expires_at"]:
                continue
            payload = {
                "grant_type": "device_auth",
                "account_id": sess["AccountID"],
                "device_id": sess["DeviceID"],
                "secret": sess["secret"],
            }
            try:
                async with http.post(
                    "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                    data=urllib.parse.urlencode(payload),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": basic_auth()
                    }
                ) as resp:
                    if resp.status == 200:
                        token = await resp.json()
                        sess["Token"] = token["access_token"]
                        sess["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=token.get("expires_in", 14400))
                        save_user(uid, sess)
                        print(f"[REFRESH] Token updated for {sess.get('Username', uid)}")
            except Exception as e:
                print(f"[ERROR] Refresh failed for {uid}: {e}")

# ---------- BOT EVENTS ----------
@bot.event
async def on_ready():
    print(f"{bot.user} online – syncing commands...")
    await bot.tree.sync()
    token_refresh.start()
    print("Bot ready! Token refresh loop started.")

# ---------- /login ----------
@bot.tree.command(name="login", description="Login to Epic via browser")
@app_commands.describe(code="Paste the exchange code")
async def login(interaction: discord.Interaction, code: str = None):
    await interaction.response.defer(ephemeral=True)
    uid = interaction.user.id

    if load_user(uid):
        await interaction.followup.send("Already logged in. Use `/logout` first.", ephemeral=True)
        return

    if not code:
        state = secrets.token_urlsafe(16)
        params = {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "scope": "basic_profile",
            "redirect_uri": REDIRECT_URI,
            "state": state,
            "response_mode": "fragment"
        }
        login_url = f"https://www.epicgames.com/id/authorize?{urllib.parse.urlencode(params)}"

        embed = discord.Embed(title="Epic Login", color=0x00ff00)
        embed.description = (
            "**Step 1:** [Click to login]({})\n"
            "**Step 2:** After login, **code is auto-copied!**\n"
            "**Step 3:** Paste here: `/login <code>`"
        ).format(login_url)
        embed.set_footer(text="Log in to Epic Games in your browser first!")
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    async with aiohttp.ClientSession() as http:
        async with http.post(
            "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
            data=urllib.parse.urlencode({
                "grant_type": "authorization_code",
                "code": code.strip(),
                "redirect_uri": REDIRECT_URI
            }),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": basic_auth()
            }
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                await interaction.followup.send(f"Invalid code:\n`{error}`", ephemeral=True)
                return
            token_data = await resp.json()

        async with http.post(
            f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{token_data['account_id']}/deviceAuth",
            headers={"Authorization": f"bearer {token_data['access_token']}"},
            json={}
        ) as resp:
            if resp.status != 200:
                await interaction.followup.send("Device auth failed.", ephemeral=True)
                return
            dev = await resp.json()

    sess = {
        "Token": token_data["access_token"],
        "AccountID": token_data["account_id"],
        "DeviceID": dev["deviceId"],
        "secret": dev["secret"],
        "Username": token_data.get("displayName", "Unknown"),
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 14400))
    }
    save_user(uid, sess)
    await interaction.followup.send(
        f"**Login Success!**\n"
        f"Logged in as **{sess['Username']}**\n"
        f"Use `/locker` or `/check` to view skins.",
        ephemeral=True
    )

# ---------- /logout ----------
@bot.tree.command(name="logout", description="Log out")
async def logout(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    p = user_path(interaction.user.id)
    if p.exists():
        p.unlink()
        await interaction.followup.send("Logged out successfully.", ephemeral=True)
    else:
        await interaction.followup.send("You were not logged in.", ephemeral=True)

# ---------- /locker (Full Skin Viewer) ----------
@bot.tree.command(name="locker", description="Show full Fortnite locker with skin names")
async def locker(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    sess = load_user(interaction.user.id)
    if not sess:
        await interaction.followup.send("Use `/login` first.", ephemeral=True)
        return

    if datetime.now(timezone.utc) >= sess["expires_at"]:
        user_path(interaction.user.id).unlink(missing_ok=True)
        await interaction.followup.send("Session expired. Please log in again.", ephemeral=True)
        return

    async with aiohttp.ClientSession() as http:
        try:
            profile = await fetch_profile(http, sess["AccountID"], sess["Token"])
        except Exception as e:
            await interaction.followup.send(f"Failed to load locker: {e}", ephemeral=True)
            return

        prof = profile.get("profileChanges", [{}])[0].get("profile", {})
        items = prof.get("items", {})
        stats = prof.get("stats", {}).get("attributes", {})

        categories = {
            "Outfits": [], "Back Blings": [], "Pickaxes": [], "Gliders": [], "Contrails": [],
            "Music Packs": [], "Loading Screens": [], "Wraps": [], "Emotes": []
        }
        vbucks = 0
        for item in items.values():
            tid = item.get("templateId", "").lower()
            if not tid: continue
            parts = tid.split(":")
            if len(parts) < 2: continue
            t, cid = parts[0], parts[1]

            if t == "athenacharacter": categories["Outfits"].append(cid)
            elif t == "athenabackpack": categories["Back Blings"].append(cid)
            elif t == "athenapickaxe": categories["Pickaxes"].append(cid)
            elif t == "athenaglider": categories["Gliders"].append(cid)
            elif t == "athenaskydivecontrail": categories["Contrails"].append(cid)
            elif t == "athenamusicpack": categories["Music Packs"].append(cid)
            elif t == "athenaloadingscreen": categories["Loading Screens"].append(cid)
            elif t == "athenaitemwrap": categories["Wraps"].append(cid)
            elif t == "athenadance": categories["Emotes"].append(cid)

            if tid.startswith("currency:mtx"):
                vbucks += item.get("quantity", 0)

        embed = discord.Embed(title=f"{interaction.user.name}'s Locker", color=0x9C59B6)
        embed.add_field(name="Level", value=str(stats.get("level", 1)), inline=True)
        embed.add_field(name="V-Bucks", value=str(vbucks), inline=True)

        total = 0
        for cat, lst in categories.items():
            total += len(lst)
            embed.add_field(name=f"{cat} ({len(lst)})", value="Check DMs for names" if lst else "None", inline=True)
        embed.add_field(name="Total Items", value=str(total), inline=False)

        await interaction.followup.send(embed=embed)

        # DM Full Skin Names
        dm = interaction.user.dm_channel or await interaction.user.create_dm()
        for cat, cids in categories.items():
            if not cids: continue
            names = []
            for cid in cids:
                data = await get_cosmetic(http, cid)
                if data:
                    names.append(f"• **{data['name']}** ({data['rarity']['displayValue']})")
                else:
                    names.append(f"• `{cid}`")
            chunks = [names[i:i+10] for i in range(0, len(names), 10)]
            for chunk in chunks:
                await dm.send(embed=discord.Embed(title=f"{cat} ({len(cids)} items)", description="\n".join(chunk), color=0x9C59B6))

# ---------- /check (EMAIL:PASS SKIN CHECKER) ----------
@bot.tree.command(name="check", description="Check Fortnite account skins via email:pass")
@app_commands.describe(account="email:password")
async def check(interaction: discord.Interaction, account: str):
    await interaction.response.defer(ephemeral=False)
    if ":" not in account:
        await interaction.followup.send("Format: `email:password`", ephemeral=True)
        return

    email, pwd = account.split(":", 1)
    async with aiohttp.ClientSession() as http:
        # Get token
        async with http.post(
            "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
            data=urllib.parse.urlencode({"grant_type": "password", "username": email, "password": pwd}),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": basic_auth()}
        ) as resp:
            if resp.status != 200:
                await interaction.followup.send(embed=discord.Embed(title="Invalid Login", description="Wrong email or password.", color=0xFF0000))
                return
            token = await resp.json()

        # Get profile
        async with http.post(
            f"https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{token['account_id']}/client/QueryProfile?profileId=athena",
            headers={"Authorization": f"bearer {token['access_token']}"}, json={}
        ) as resp:
            if resp.status != 200:
                await interaction.followup.send(embed=discord.Embed(title="Profile Error", color=0xFF0000))
                return
            prof = (await resp.json()).get("profileChanges", [{}])[0].get("profile", {})
            items = prof.get("items", {})
            stats = prof.get("stats", {}).get("attributes", {})

            # Count skins
            outfits = [i for i in items.values() if i.get("templateId", "").lower().startswith("athenacharacter:")]
            vbucks = sum(i.get("quantity", 0) for i in items.values() if i.get("templateId", "").lower().startswith("currency:mtx"))

            embed = discord.Embed(title="Account Valid", color=0x00FF00)
            embed.add_field(name="Name", value=token.get("displayName", "Unknown"), inline=True)
            embed.add_field(name="Skins", value=str(len(outfits)), inline=True)
            embed.add_field(name="V-Bucks", value=str(vbucks), inline=True)
            embed.add_field(name="Level", value=str(stats.get("level", 1)), inline=True)

            # List top 5 skins
            if outfits:
                top_skins = []
                for item in outfits[:5]:
                    cid = item["templateId"].split(":")[1]
                    data = await get_cosmetic(http, cid)
                    name = data["name"] if data else cid
                    top_skins.append(f"• **{name}**")
                embed.add_field(name="Top Skins", value="\n".join(top_skins), inline=False)

            await interaction.followup.send(embed=embed)

# ---------- /generate ----------
@bot.tree.command(name="generate", description="Get account from stock")
@app_commands.describe(stock="free or premium")
async def generate(interaction: discord.Interaction, stock: str = None):
    await interaction.response.defer(ephemeral=False)
    user = interaction.user
    if stock not in ("free", "premium"):
        if discord.utils.get(user.roles, name=PAID_ROLE):
            stock = "premium"
        elif discord.utils.get(user.roles, name=FREE_ROLE):
            stock = "free"
        else:
            await interaction.followup.send("You need a role.", ephemeral=True)
            return

    avail = load_stock(stock)
    if not avail:
        await interaction.followup.send(f"No `{stock}` accounts left.", ephemeral=False)
        return

    line = random.choice(avail)
    mark_used(stock, line)
    email, pwd = line.split(":", 1)
    embed = discord.Embed(title=f"{stock.title()} Account", color=0x00ff00)
    embed.add_field(name="Email", value=email)
    embed.add_field(name="Password", value=pwd)
    await interaction.followup.send(embed=embed, ephemeral=False)

# ---------- ADMIN ----------
@bot.tree.command(name="create_stock", description="Create stock file")
@app_commands.describe(name="Stock name")
async def create_stock(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    if not discord.utils.get(interaction.user.roles, name=ADMIN_ROLE):
        await interaction.followup.send("Admin only.", ephemeral=True)
        return
    Path(f"stock_{name}.txt").touch()
    Path(f"used_{name}.txt").touch()
    await interaction.followup.send(f"Created `{name}` stock.", ephemeral=True)

@bot.tree.command(name="add_account", description="Add account to stock")
@app_commands.describe(account="email:pass", stock_name="Stock name")
async def add_account(interaction: discord.Interaction, account: str, stock_name: str = "free"):
    await interaction.response.defer(ephemeral=True)
    if not discord.utils.get(interaction.user.roles, name=ADMIN_ROLE):
        await interaction.followup.send("Admin only.", ephemeral=True)
        return
    file = Path(f"stock_{stock_name}.txt")
    file.write_text(file.read_text(encoding="utf-8", errors="ignore") + account + "\n", encoding="utf-8")
    await interaction.followup.send(f"Added to `{stock_name}`.", ephemeral=True)

# ---------- RUN ----------
if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("ERROR: Set your Discord bot token!")
    else:
        bot.run(TOKEN)