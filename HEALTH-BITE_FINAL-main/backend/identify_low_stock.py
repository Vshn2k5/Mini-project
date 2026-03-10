import sqlite3

def check():
    conn = sqlite3.connect('canteen.db')
    cursor = conn.cursor()
    
    print("--- LOW STOCK ITEMS ---")
    # Low stock: stock > 0 and stock < reorder_level
    cursor.execute("""
        SELECT f.name, i.current_stock, i.reorder_level 
        FROM inventory i
        JOIN food_items f ON i.food_id = f.id
        WHERE i.current_stock > 0 AND i.current_stock < i.reorder_level
    """)
    low = cursor.fetchall()
    for row in low:
        print(f"Item: {row[0]} | Stock: {row[1]} | Reorder Level: {row[2]}")
        
    print("\n--- OUT OF STOCK ITEMS ---")
    # Out of stock: stock == 0
    cursor.execute("""
        SELECT f.name, i.current_stock, i.reorder_level 
        FROM inventory i
        JOIN food_items f ON i.food_id = f.id
        WHERE i.current_stock = 0
    """)
    oos = cursor.fetchall()
    for row in oos:
        print(f"Item: {row[0]} | Stock: {row[1]} | Reorder Level: {row[2]}")
    
    conn.close()

if __name__ == "__main__":
    check()
