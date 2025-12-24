
def cost(price, count):
    cost = 0

    if count["apple"]%2==0:
        cost += price["apple"]*(count["apple"] / 2)
    elif count["apple"]%2 == 1:
        cost += price["apple"]*(int(count["apple"] / 2)) + int(price["apple"])
    elif count["banana"]%2==0:
        cost += price["banana"]*(count["banana"] / 2)
    elif count["banana"]%2==1:
        cost += price["banana"]*(int(count["banana"] / 2)) + price["banana"]
    elif count["melon"]%2 == 0:
        cost += price["melon"]*(count["melon"]/2)
    elif count["melon"]%2 == 1:
        cost += price["melon"]*(count["melon"]/2) + price["melon"]
    elif count["lime"]%3==0:
         cost += price["lime"]*(count["lime"] / 3)
    elif count["lime"]%3 != 0:
        cost += price["lime"]*(count["lime"]/3)*2 + price["lime"]*(count["lime"]%3) 
    print(cost)


def main():
    price = {
        "apple" : 35, 
        "banana" : 20, 
        "melon" : 50,
        "lime" : 15  
    }

    count_apple = 0
    count_banana =0
    count_lime =0
    count_melon =0

    basket = ["apple","banana"]

    for fruit in basket:
        if fruit == "apple":
            count_apple+=1
        if fruit == "banana":
            count_banana+=1
        if fruit == "melon":
            count_melon+=1
        if fruit == "lime":
            count_lime+=1

    count = {}
    count["apple"] = count_apple
    count["banana"] = count_banana
    count["lime"] = count_lime
    count["melon"] = count_melon

    print(count)

    cost(price, count)

if __name__ == '__main__':
    main()