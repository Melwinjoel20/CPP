from Main import shop
a_cap = int(input ("Enter the number of caps:"))
a_shirt = int(input("Enter the number of shirts:"))
a_hoodie = int(input("Enter the number of hoodies:"))


obj = shop(a_cap, a_shirt, a_hoodie)
print("Total Cap Cost", obj.fn_caps())
print("Total Shirt Cost", obj.fn_shirt())
print("Total Cap Hoodie", obj.fn_hoodie())
print("Grand Total", obj.grand_total())