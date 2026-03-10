import sqlite3

def check():
    conn = sqlite3.connect('canteen.db')
    cursor = conn.cursor()
    
    print("--- INVENTORY ---")
    cursor.execute("SELECT id, food_id, current_stock, reorder_level FROM inventory")
    inv = cursor.fetchall()
    for row in inv:
        if row[2] < row[3]:
            print(f"!!! DISCREPANCY: {row}")
        else:
            # print(row)
            pass
        
    print("\n--- SUMMARY COUNTS ---")
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE current_stock = 0")
    oos = cursor.fetchone()[0]
    print(f"Out of Stock (stock == 0): {oos}")
    
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE current_stock > 0 AND current_stock < reorder_level")
    ls = cursor.fetchone()[0]
    print(f"Low Stock (stock > 0 and stock < reorder): {ls}")
    
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE current_stock < reorder_level")
    both = cursor.fetchone()[0]
    print(f"Total Below Reorder (stock < reorder): {both}")
    
    conn.close()

if __name__ == "__main__":
    check()
