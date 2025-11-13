// tokenRefresh.js
const fs = require('fs').promises;
const path = require('path');
const axios = require('axios');

const CLIENT_ID = '34a02cf8f4414e29b15921876da36f9a';
const CLIENT_SECRET = 'daafbccc737745039dffe53d94fc76cf';
const BASIC_AUTH = Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString('base64');

async function refreshTokens() {
  const usersDir = path.join(__dirname, 'users');
  const files = await fs.readdir(usersDir).catch(() => []);
  const now = Date.now();

  for (const file of files) {
    if (!file.endsWith('.json')) continue;
    const filePath = path.join(usersDir, file);
    const data = JSON.parse(await fs.readFile(filePath, 'utf-8'));

    if (now >= data.expires_at) {
      try {
        const payload = new URLSearchParams({
          grant_type: 'device_auth',
          account_id: data.AccountID,
          device_id: data.DeviceID,
          secret: data.secret,
        }).toString();

        const res = await axios.post(
          'https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token',
          payload,
          {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
              Authorization: `Basic ${BASIC_AUTH}`,
            },
          }
        );

        data.Token = res.data.access_token;
        data.expires_at = Date.now() + res.data.expires_in * 1000;
        await fs.writeFile(filePath, JSON.stringify(data, null, 2));
        console.log(`Refreshed token: ${data.Username}`);
      } catch (e) {
        console.error(`Failed refresh ${file}:`, e.response?.data || e.message);
      }
    }
  }
}

setInterval(refreshTokens, 30 * 60 * 1000);
refreshTokens(); // Run on start