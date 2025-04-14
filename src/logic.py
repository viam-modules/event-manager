from typing import List

def OR(list: List[bool]) -> bool:
  for item in list:
    if item == True:
      return True
  return False

def AND(list: List[bool]) -> bool:
  if len(list) == 0:
    return False
  result = True
  for item in list:
    if item == False:
      result = False
  return result

def XOR(list: List[bool]) -> bool:
  true_count = 0
  for item in list:
    if item == True:
      true_count = true_count + 1
  if true_count == 1:
    return True
  return False

def NAND(list: List[bool]) -> bool:
  return not AND(list)

def NOR(list: List[bool]) -> bool:
  return not OR(list)

def XNOR(list: List[bool]) -> bool:
  return not XOR(list)