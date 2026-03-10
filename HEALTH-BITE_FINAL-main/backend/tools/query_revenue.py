import os, sqlite3
from datetime import datetime

db_path = os.path.join(os.path.dirname(__file__), 'canteen.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# print all orders and revenue today
now = datetime.now()
start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
end = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
print('today range', start, end)
rows = c.execute("SELECT id, total_price, created_at FROM orders WHERE created_at >= ? AND created_at <= ?", (start, end)).fetchall()
print('orders today:')
for r in rows:
    print(r)
print('sum', sum(r[1] or 0 for r in rows))

# count canceled and other statuses
rows2 = c.execute("SELECT id, status, total_price FROM orders WHERE created_at >= ? AND created_at <= ?", (start, end)).fetchall()
print('status breakdown:')
from collections import Counter
print(Counter((r[1],) for r in rows2))
conn.close()
