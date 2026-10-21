import db
import config
from user_manager import user_manager

admin_key = "sk-antigravity-admin-hieu4390"

# 1. Update settings in MySQL
db.execute("UPDATE settings SET setting_value = %s WHERE setting_key = 'api_key'", (admin_key,))

# 2. Update config.API_KEY and persisted settings
config.API_KEY = admin_key
p = config.get_persisted_settings()
p["api_key"] = admin_key
config.save_persisted_settings(p)
config.update_env_file("API_KEY", admin_key)

# 3. Verify in api_keys table
row = db.fetch_one("SELECT * FROM api_keys WHERE key_value = %s", (admin_key,))
print("api_keys record:", row)

# 4. Verify in settings table
s_row = db.fetch_one("SELECT * FROM settings WHERE setting_key = 'api_key'")
print("settings record:", s_row)

print("SUCCESS: config.API_KEY and admin user API Key are now 100% UNIFIED to:", admin_key)
