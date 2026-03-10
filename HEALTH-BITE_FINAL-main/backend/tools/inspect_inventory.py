import os
import sqlite3
# ensure we open the correct DB file even when cwd is workspace root
conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'canteen.db'))
c = conn.cursor()
print('Inventory rows:')
for row in c.execute('SELECT id,food_id,current_stock,reorder_level FROM inventory'):
    print(row)
print('Count low stock>0<reorder:')
print(c.execute('SELECT count(*) FROM inventory WHERE current_stock>0 AND current_stock<reorder_level').fetchone())
print('Count current<reorder:')
print(c.execute('SELECT count(*) FROM inventory WHERE current_stock<reorder_level').fetchone())
print('Count current=0:')
print(c.execute('SELECT count(*) FROM inventory WHERE current_stock=0').fetchone())
conn.close()