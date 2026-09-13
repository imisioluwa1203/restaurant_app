print("---ACiD'S TREATS----")

     #we add the menu in a dictionary
Orders= {'Rice': 500,
         'Beans': 300,
         'Pasta': 200,
         'Pizza' : 15000,
         'Sharwama': 3000
         }

unavailable_food = ['Amala','Egg']
Ordered_food = []
total_amount_ordered = 0

      # We loop through our orders /Showing the menu to our customer
def show_menu():

   for food,price in Orders.items():
     print(food, "-", price)
     # lets collect order from our customer

def print_receipt():
    print("Ordered_food :", Ordered_food)
    print("Total amount of Food Ordered is : ", total_amount_ordered)

def add_order(type_of_order,Quantity, notes=""):
    global total_amount_ordered
    found = False
    for i,item in enumerate(Ordered_food):
        quantity,food = item.split()[0], item.split()[1]
        if food == type_of_order:
            new_quantity = int(quantity) + Quantity
            note_part = f" ({notes})" if notes else ""
            Ordered_food[i] = f"{new_quantity} {food}{note_part}"
            found = True
            break
    if not found:
        note_part = f" ({notes})" if notes else ""
        Ordered_food.append(f"{Quantity} {type_of_order}{note_part}")
    print('Food Added Successfully:', Quantity,type_of_order, notes)
    total_amount_ordered += Orders[type_of_order] * Quantity

def remove_order(food_to_remove, remove_quantity):
    global total_amount_ordered
    found = False
    for item in Ordered_food:
        parts = item.split()
        quantity = parts[0]
        food = parts[1]
        note_part = " " + " ".join(parts[2:]) if len(parts) > 2 else ""

        if food == food_to_remove:
            quantity = int(quantity)
            if remove_quantity < quantity:
                new_quantity = quantity - remove_quantity
                Ordered_food.remove(item)
                Ordered_food.append(f"{new_quantity} {food}{note_part}")
                total_amount_ordered -= Orders[food] * remove_quantity
                print(f"Removed {remove_quantity} from {food}")
            elif remove_quantity == quantity:
                Ordered_food.remove(item)
                total_amount_ordered -= Orders[food] * remove_quantity
                print(f"{food} removed Completely")
            else:
                print("Food exceed Ordered!!!")
            found = True
            break

    if not found:
        print("Order not found")



# we call out our function
if __name__ == '__main__':
    show_menu()

    while True:

         order_place = input("Place your order: ")

         parts = order_place.split()
         # Stop ordering
         if order_place.lower() == 'done':
             break
         # Remove conditions
         if parts[0] == "remove":
             if len(parts) == 2:
                 remove_quantity = 1
                 food_to_remove= parts[1].capitalize()
             else:
                   remove_quantity = int(parts[1])
                   food_to_remove = parts[2].capitalize()

             remove_order(food_to_remove,remove_quantity)
             continue

             #Add Order
         if len(parts) == 1:
            Quantity = 1
            type_of_order = parts[0].capitalize()
         else:
            Quantity = int(parts[0])
            type_of_order = parts[1].capitalize()

         if type_of_order in unavailable_food:
                  print("Out of stock")

         elif type_of_order in Orders:
              add_order(type_of_order, Quantity)
         else:
             print("Food not available")
    print_receipt()
