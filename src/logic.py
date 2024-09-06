def OR(list):
  for item in list:
    if item == True:
      return True
  return False

def AND(list):
  result = True
  for item in list:
    if item == False:
      result = False
  return result

def XOR(list):
  true_count = 0
  for item in list:
    if item == True:
      true_count = true_count + 1
  if true_count == 1:
    return True
  return False

def NAND(list):
  return not AND(list)

def NOR(list):
  return not OR(list)

def XNOR(list):
  return not XOR(list)