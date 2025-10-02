from Main import user_details
a_age = int(input ("Enter the age:"))
a_height = int(input("Enter the height:"))

Weight = user_details(a_age, a_height)
obj = Weight.weight()
print(obj)
