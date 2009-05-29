
# pylint: disable-msg=W0104,R0914

#public symbols
__all__ = ["ExprEvaluator"]

__version__ = "0.1"


#from __future__ import division

import weakref
import math

from pyparsing import Word, ZeroOrMore, OneOrMore, Literal, CaselessLiteral
from pyparsing import oneOf, alphas, nums, alphanums, Optional, Combine
from pyparsing import Forward, StringEnd
from pyparsing import ParseException

def _trans_unary(strng, loc, tok):
    return tok

    
def _trans_lhs(strng, loc, tok, exprobj):
    scope = exprobj._scope()
    lazy_check = exprobj.lazy_check
    if scope.contains(tok[0]):
        scname = 'scope'
    else:
        scname = 'scope.parent'
        if hasattr(scope, tok[0]):
            scope.warning("attribute '"+tok[0]+"' is private"+
                          " so a public value in the parent is"+
                          " being used instead (if found)")
        if lazy_check is False and not scope.parent.contains(tok[0]):
            raise RuntimeError("cannot find variable '"+tok[0]+"'")
        
        exprobj._register_output(tok[0])
        
    full = scname + ".set('" + tok[0] + "',_@RHS@_"
    if len(tok) > 1 and tok[1] != '=':
        full += ","+tok[1]
            
    return ['=', full + ")"]
    
def _trans_assign(strng, loc, tok, exprobj):
    if tok[0] == '=':
        exprobj.lhs = tok[1].replace('_@RHS@_', '', 1)
        exprobj.rhs = tok[2]
        return [tok[1].replace('_@RHS@_', tok[2], 1)]
    else:
        exprobj.lhs = ''.join(tok)
        return tok
    
def _trans_arrayindex(strng, loc, tok):
    full = "[" + tok[1]
    if tok[2] == ',':
        for index in range(3, len(tok), 2):
            full += ','
            full += tok[index]
    else:
        for index in range(4, len(tok), 3):
            full += ','
            full += tok[index]
    return [full+"]"]
    
def _trans_arglist(strng, loc, tok):
    full = "("
    if len(tok) > 2: 
        full += tok[1]
    for index in range(3, len(tok), 2):
        full += ','+tok[index]
    return [full+")"]

def _trans_fancyname(strng, loc, tok, exprobj):
    # if we find the named object in the current scope, then we don't need to 
    # do any translation.  The scope object is assumed to have a contains() 
    # function.
    scope = exprobj._scope()
    lazy_check = exprobj.lazy_check
    
    if scope.contains(tok[0]):
        scname = 'scope'
        if hasattr(scope, tok[0]):
            return tok  # use name unmodified for faster local access
    elif tok[0] == '_local_setter': # used in assigment statements
        return tok
    else:
        scname = 'scope.parent'
        if hasattr(scope, tok[0]):
            scope.warning("attribute '%s' is private" % tok[0]+
                          " so a public value in the parent is"+
                          " being used instead (if found)")
        if lazy_check is False and (scope.parent is None or 
                                 not scope.parent.contains(tok[0])):
            raise RuntimeError("cannot find variable '"+tok[0]+"'")
    
        exprobj._register_input(tok[0])
        
    if len(tok) == 1 or (len(tok) > 1 and tok[1].startswith('[')):
        full = scname + ".get('" + tok[0] + "'"
        if len(tok) > 1:
            full += ","+tok[1]
    else:
        full = scname + ".invoke('" + tok[0] + "'"
        if len(tok[1]) > 2:
            full += "," + tok[1][1:-1]
        
    return [full + ")"]
    

def translate_expr(text, exprobj, single_name=False):
    """A function to translate an expression using dotted names into a new
    expression string containing the appropriate calls to resolve those dotted
    names in the framework, e.g., 'a.b.c' becomes get('a.b.c') or 'a.b.c(1,2,3)'
    becomes invoke('a.b.c',1,2,3).
    """
    scope = exprobj._scope()
    lazy_check = exprobj.lazy_check
    
    ee = CaselessLiteral('E')
    comma    = Literal( "," )    
    plus     = Literal( "+" )
    minus    = Literal( "-" )
    mult     = Literal( "*" )
    div      = Literal( "/" )
    lpar     = Literal( "(" )
    rpar     = Literal( ")" )
    dot      = Literal( "." )
#    equal    = Literal( "==" )
#    notequal = Literal( "!=" )
#    less     = Literal( "<" )
#    lesseq   = Literal( "<=" )
#    greater  = Literal( ">" )
#    greatereq = Literal( ">=" )
    
    assignop = Literal( "=" )
    lbracket = Literal( "[" )
    rbracket = Literal( "]" )
    expop    = Literal( "**" )

    expr = Forward()
    arrayindex = Forward()
    arglist = Forward()
    fancyname = Forward()

    digits = Word(nums)

    number = Combine( ((digits + Optional( dot + Optional(digits) )) |
                             (dot + digits) )+
                           Optional( ee + Optional(oneOf('+ -')) + digits )
                          )
    name = Word('_'+alphas, bodyChars='_'+alphanums)
    pathname = Combine(name + ZeroOrMore(dot + name))
    arrayindex << OneOrMore(lbracket + Combine(expr) + 
                            ZeroOrMore(comma+Combine(expr)) + rbracket)
    arrayindex.setParseAction(_trans_arrayindex)
    arglist << lpar + Optional(Combine(expr) + 
                               ZeroOrMore(comma+Combine(expr))) + rpar
    arglist.setParseAction(_trans_arglist)
    fancyname << pathname + ZeroOrMore(arrayindex | arglist)
    
    # set up the scope name translation here. Parse actions called from
    # pyparsing only take 3 args, so we wrap our function in a lambda function
    # with extra arguments to specify the scope used for the translation,
    # the validation flag, and the ExprEvaluator object.
    fancyname.setParseAction(
        lambda s,loc,tok: _trans_fancyname(s,loc,tok,exprobj))

    addop  = plus | minus
    multop = mult | div
#    boolop = equal | notequal | less | lesseq | greater | greatereq

    factor = Forward()
    atom = Combine(Optional("-") + (( number | fancyname) | (lpar+expr+rpar)))
    factor << atom + ZeroOrMore( ( expop + factor ) )
    term = factor + ZeroOrMore( ( multop + factor ) )
    expr << term + ZeroOrMore( ( addop + term ) )
    
    lhs_fancyname = pathname + ZeroOrMore(arrayindex)
    lhs = lhs_fancyname + assignop
    lhs.setParseAction(lambda s,loc,tok: _trans_lhs(s,loc,tok,exprobj))
    equation = Optional(lhs) + Combine(expr) + StringEnd()
    equation.setParseAction(lambda s,loc,tok: _trans_assign(s,loc,tok, exprobj))
    
    try:
        if single_name:
            simple_str = fancyname + StringEnd()
            return ''.join(simple_str.parseString(text))
        else:
            return ''.join(equation.parseString(text))
    except ParseException, err:
        raise RuntimeError(str(err)+' - '+err.markInputline())

    
class ExprEvaluator(object):
    """A class that translates an expression string into a new string containing
    any necessary framework access functions, e.g., set, get. The compiled
    bytecode is stored within the object so that it doesn't have to be reparsed
    during later evaluations.  A scoping object is required at construction time
    and that object determines the form of the  translated expression. 
    Variables that are local to the scoping object do not need to be translated,
    whereas variables from other objects must  be accessed using the appropriate
    set() or get() call.  Array entry access and function invocation are also
    translated in a similar way.  For example, the expression "a+b[2]-comp.y(x)"
    for a scoping object that contains attributes a and b, but not comp,x or y,
    would translate to 
    "a+b[2]-self.parent.invoke('comp.y',self.parent.get('x'))".
    
    If lazy_check is False, any objects referenced in the expression must exist
    at creation time (or any time later that text is set to a different value)
    or a RuntimeError will be raised.  If lazy_check is True, error reporting will
    be delayed until the expression is evaluated.
    
    If single_name is True, the expression can only be the name one object, with
    optional array indexing, but general expressions are not allowed.
    """
    
    def __init__(self, text, scope, single_name=False, lazy_check=False):
        self._scope = weakref.ref(scope)
        self.input_names = set()
        self.output_names = set()
        self.lazy_check = lazy_check
        self.single_name = single_name
        self.text = text  # this calls _set_text
        self.rhs = ''
        self.lhs = ''
    
    def __getstate__(self):
        """Return dict representing this container's state."""
        state = self.__dict__.copy()
        if state['_scope'] is not None:
            # remove weakref to scope because it won't pickle
            state['_scope'] = self._scope()
        state['_code'] = None  # <type 'code'> won't pickle either.
        return state

    def __setstate__(self, state):
        """Restore this component's state."""
        self.__dict__ = state
        if self._scope is not None:
            self._scope = weakref.ref(self._scope)
        if self.scoped_text:
            self._code = compile(self.scoped_text, '<string>', 'eval')

    def _set_text(self, text):
        self._text = text
        self.input_names = set()
        self.output_names = set()
        self.scoped_text = translate_expr(text, self, 
                                          single_name=self.single_name)
        self._code = compile(self.scoped_text, '<string>','eval')
        if self.single_name: # set up a compiled assignment statement
            old_lazy_check = self.lazy_check
            try:
                self.lazy_check = True
                self.scoped_assignment_text = translate_expr(
                                            '%s = _local_setter' % self.text, 
                                            self)
                self._assignment_code = compile(self.scoped_assignment_text, 
                                                '<string>','exec')
            finally:
                self.lazy_check = old_lazy_check
        
    def _get_text(self):
        return self._text
    
    text = property(_get_text, _set_text, None,
                    'The untranslated text of the expression')
        
    def evaluate(self):
        """Return the value of the scoped string, evaluated 
        using the eval() function.
        """
        scope = self._scope()
        
        # object referred to by weakref may no longer exist
        if scope is None:
            raise RuntimeError(
                    'ExprEvaluator cannot evaluate expression without scope.')
        try:
            return eval(self._code, scope.__dict__, locals())
        except Exception, err:
            raise type(err)("ExprEvaluator failed evaluating expression "+
                            "'%s'. Caught message is: %s" %(self._text,str(err)))

    def set(self, val):
        """Set the value of the referenced object to the specified value."""
        if self.single_name:
            scope = self._scope()
            # object referred to by weakref may no longer exist
            if scope is None:
                raise RuntimeError(
                    'ExprEvaluator cannot evaluate expression without scope.')
            
            # self.assignment_code is a compiled version of an assignment statement
            # of the form  'somevar = _local_setter', so we set _local_setter here
            # and the exec call will pull it out of locals()
            _local_setter = val 
            exec(self._assignment_code, scope.__dict__, locals())            
        else: # self.single_name is False
            raise ValueError('trying to set an input expression')
        
    def _register_input(self, name):
        """Adds a Variable name to the input set. 
        Called during expression parsing.
        """
        self.input_names.add(name)
    
    def _register_output(self, name):
        """Adds a Variable name to the output set. 
        Called during expression parsing.
        """
        self.output_names.add(name)
