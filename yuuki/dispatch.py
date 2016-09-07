import collections
import warnings
import imp


class Dispatcher(object):
    """
    Construct a Dispatcher from profiles (paths to python modules)
    
    TODO: warn on shadowing an existing definition from another module
    TODO: fix bug - spreading the logic for one action across multiple
    modules does not work properly
    """
    def __init__(self, *profiles):
        self.modules = collections.deque()
        for module in profiles:
            self.modules.appendleft(imp.load_source('profile', module))


    def dispatch(self, cmd):
        """
        Call the appropriate function defined in an OpenC2 profile
        and provide the OpenC2 command details to said method.

        TODO: better error handling
        TODO: autogenerate the response to a query requesting this
        OpenC2 actuator's capabilities. Plan is to generate this info
        from the multimethod docstrings
        """
        target = cmd['target']
        actuator = cmd.get('actuator')
        modifier = cmd.get('modifier')
        
        f = None
        for module in self.modules:
            if hasattr(module, cmd['action']):
                f = getattr(module, cmd['action'])
                break
        else:
            raise NameError(str(cmd['action']
                            + " is not defined for types provided"))
        
        return f(target, actuator, modifier)


class OpenC2Action(object):
    """
    OpenC2Action is a custom multimethod implementation
    
    An OpenC2Action dispatches on args[0]['type'] and, optionally,
    args[1]['type']. In OpenC2 semantics, this corresponds to the type
    of the target (required) and the type of the actuator. The default
    actuator is None
    
    TODO: better warning/error messages; docstring handling
    """
    def __init__(self, name):
        self.name = name
        self.table = {}
        self._last_register = None


    def __call__(self, *args):
        target_type = args[0].get('type')
        
        actuator_type = None
        if args[1] is not None:
            actuator_type = args[1].get('type')

        function = self.table.get((target_type, actuator_type))
        
        if function is None:
            raise TypeError("No definition for signature")

        return function(*args)


    def register(self, target_types, actuator_types, function):
        """
        Register target_types X actuator_types with function in this
        multimethod's dispatch table.
        """
        signatures = [(t_type, a_type) for t_type in target_types
                                       for a_type in actuator_types]
        
        for signature in signatures:
            if signature in self.table:
                warnings.warn("Replacing existing definition for...")
            
            self.table[signature] = function


def action(target, actuator=None):
    """
    Decorator for OpenC2 target and actuator types.
    """
    def register(function):
        name = function.__name__
        current_def = function.__globals__.get(name)
        
        if current_def is None:
            current_def = OpenC2Action(name)
        
        target_types = target
        if not isinstance(target, list):
            target_types = [target]
        
        actuator_types = actuator
        if not isinstance(actuator, list):
            actuator_types = [actuator]

        current_def.register(target_types, actuator_types, function)

        return current_def

    return register

