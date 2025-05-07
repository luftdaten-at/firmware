# -*- coding: utf-8 -*-


class MixinAccess:
    """
    This class allows to declare names for mixin base classes. In this way the function from these base classes
    can be called with the syntax self.<name>.function(*args) instead of mixin_class.function(self,*args)
    or super(prev, self).function(*args)
    The base class access is supposed to work for function calls.

    This allows to have a uniform access to the mixins without relaying on a specific class name
    or on an initialization order of the base classes.
    """

    def __init__(self, base_class = None):
        """
        Initializes the access to the mixin class.
        In case only one base class is there, the base_class parameter can be omitted.
        """
        self._base_class = base_class
        self._preceding_base = None  # caches result of lookup

    def __get__(self, instance, instance_type):
        if self._base_class is None:
            return super(instance_type, instance)
        return self.get_super(instance_type, instance)

    def get_super(self, instance_type, instance):
        if self._preceding_base is None:
            base = instance_type
            for cls in instance_type.__bases__:
                if cls == self._base_class:
                    # the order in which the base classes are defined is important!
                    # super is supposed to access the base class that follows after the class used as argument
                    self._preceding_base = base
                    break
                base = cls
            if self._preceding_base is None:
                raise NotImplementedError("illegal base class access")
        return super(self._preceding_base, instance)
