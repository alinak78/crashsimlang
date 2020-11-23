from register_automaton import RegisterAutomaton
from register_automaton import State
from register_automaton import Transition
from dataword import DataWord
from adt import ContainerBuilder
from cslang_error import CSlangError
import dill as pickle

def process_root(ast_root):
  automaton = RegisterAutomaton()
  container_builder = ContainerBuilder()
  for i in ast_root:
    if i[0] == "REGASSIGN":
      # identifier, value
      handle_regassign(automaton, i[1][1], i[2])
    elif i[0] == "TYPEDEF":
      # type_name, list of contained types
      handle_typedef(container_builder, i[1], i[2])
    elif i[0] == "DATAWORD":
      # HACK: "the rest of the stuff to build a dataword"
      handle_dataword(automaton, i[1:])
    else:
      raise NotImplementedError("Not implemented node: {}".format(i[0]))
  automaton.states[-1].is_accepting = True
  return automaton, container_builder

def handle_regassign(automaton, register_name, value):
  if value[0] == 'IDENTIFIER':
    automaton.registers[register_name] = automaton.registers[value[1]]
  elif value[0] in ['NUM_LITERAL', 'NUMERIC']:
    automaton.registers[register_name] = float(value[1])
  elif value[0] == 'STRING_LITERAL':
    automaton.registers[register_name] = str(value[1])
  elif value[0] == 'REGEXP':
    automaton.registers[register_name] = _get_expression_value(automaton, value[1])
  else:
    raise CSlangError("Bad type in register assignment: {}".format(value[0]))

def _get_expression_value(automaton, exp):
  lhs = exp[1]
  rhs = exp[3]

  if lhs[0] == "REGEXP":
    lhs = _get_expression_value(automaton, lhs)

  if rhs[0] == "REGEXP":
    rhs = _get_expression_value(automaton, rhs)

  if lhs[0] == "IDENTIFIER":
   lhs = _value_from_register(automaton, lhs[1])
  else:
   lhs = _to_num_or_str(lhs)

  if rhs[0] == "IDENTIFIER":
   rhs = _value_from_register(automaton, rhs[1])
  else:
   rhs = _to_num_or_str(rhs)


  if lhs[0] != rhs[0]:
    raise CSlangError("Type mismatch between registers {} and {}"
                      .format(exp[1], exp[1]))

  if exp[0] in ["REGADD", "REGCONCAT"]:
    if lhs[0] == "String":
      return  str(lhs[1]) + str(rhs[1])
    elif lhs[0] == "Numeric":
      return float(lhs[1]) + float(rhs[1])
    else:
      raise CSlangError("Bad type in addition/concatination: {}".format(lhs[0]))
  elif exp[0] == "REGSUB":
    if lhs[0] != "Numeric" or rhs[0] != "Numeric":
      raise CSlangError("Bad type in subtraction: {}".format(lhs[0]))
    return float(lhs[1]) - float(rhs[1])
  elif exp[0] == "REGMUL":
    if lhs[0] != "Numeric" or rhs[0] != "Numeric":
      raise CSlangError("Bad type in multiplication: {}".format(lhs[0]))
    return float(lhs[1]) * float(rhs[1])
  elif exp[0] == "REGDIV":
    if lhs[0] != "Numeric" or rhs[0] != "Numeric":
      raise CSlangError("Bad type in division: {}".format(lhs[0]))
    return float(lhs[1]) / float(rhs[1])
  else:
    raise CSlangError("Bad expression operation: {}".format(exp[0]))


def _value_from_register(automaton, reg):
  val = automaton.registers[reg]
  if type(val) == str:
    return ("String", val)
  elif type(val) == float:
    return ("Numeric", val)
  else:
    raise CSlangError("Got bad type out of register value: {}, {}".format(val, type(val)))



def _to_num_or_str(val):
  if val[0] in ["Numeric", "NUM_LITERAL"]:
    return ("Numeric", val[1])
  elif val[0] in ["String", "STRING_LITERAL"]:
    return ("String", val[1])
  else:
    raise CSlangError("Bad type in cast to String or Numeric: {}".format(val[0]))

def handle_typedef(cb, type_name, type_definition):
  cb.define_type(type_name, type_definition)

def handle_dataword(automaton, params):
  if params[0] == "NOT":
    not_dataword = True
    syscall_name = params[1]
    operations = params[2][1]
    if len(params) == 4:
      predicates = params[3][1:]
    else:
      predicates = None
  else:
    not_dataword = False
    syscall_name = params[0]
    operations = params[1][1]
    if len(params) == 3:
      predicates = params[2][1:]
    else:
      predicates = None


  if not_dataword:
    #  This is a not dataword so we create our NOT state
    automaton.states.append(State(syscall_name, tags=["NOT"]))

    # And make a transition to it with appropriate register_matches
    automaton.states[-2].transitions.append(Transition(syscall_name,
                                            len(automaton.states) - 1,
                                            operations=operations))

  else:
    # We encountered a new dataword so we make a new state
    automaton.states.append(State(syscall_name, operations))

    # We create a transition to this state on the previous state

    # The state we just added is in automaton.states[-1] so we need to start
    # with automaton.states[-2] and keep searching back until we hit a non-NOT
    # state.  This is the state to which we will add a transition to the new state
    # we just added.

    neg_index = -2
    while "NOT" in automaton.states[neg_index].tags:
      neg_index -= 1

    automaton.states[neg_index].transitions.append(Transition(syscall_name,
                                                              len(automaton.states) - 1,
                                                              operations=operations,
                                                              predicates=predicates))
