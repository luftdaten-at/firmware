# -*- coding: utf-8 -*-
# (c) Copyright 2022 Sensirion AG, Switzerland

from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from functools import partial, partialmethod
from typing import TypeVar, Callable, Type

from sensirion_driver_adapters.channel import AbstractMultiChannel

T1 = TypeVar("T1")
T2 = TypeVar("T2")


class MultiChannelWrapper(ABC):

    def __init__(self, driver_type: type, execute_parallel: bool) -> None:
        self._current_fun = None
        self._wrap_fun = MultiChannelWrapper.__co_repeat__ if execute_parallel else MultiChannelWrapper.__repeat__
        self._driver_type = driver_type
        self._drivers = []
        assert isinstance(self._channel, AbstractMultiChannel), "Multi Drivers must be used with AbstractMultiChannel"
        for i in range(self._channel.channel_count):
            driver = object.__new__(driver_type)
            driver.__init__(self.channel.get_channel(i))
            self._drivers.append(driver)

    @staticmethod
    def __repeat__(*args, me, fun_name, **kwargs):
        results = []
        with me.channel:
            for driver in me._drivers:
                fun = getattr(driver, fun_name)
                results.append(fun(*args, **kwargs))
        return tuple(results)

    @staticmethod
    def __co_repeat__(*args, me, fun_name, **kwargs):
        calls = [getattr(driver, fun_name) for driver in me._drivers]
        with me.channel:
            with ThreadPoolExecutor(max_workers=me.channel.channel_count) as executor:
                futures = [executor.submit(fun, *args, **kwargs) for fun in calls]
                return tuple(map(lambda x: x.result(), futures))

    def __getattribute__(self, item):
        attr = object.__getattribute__(self, item)
        # for these attributes we want to have normal attribute behavior
        if not callable(attr) or item in ['__repeat__', '__co_repeat__', '__wrapped_type__', '_wrap_fun']:
            return attr
        # calls to methods of the new type do not need to be wrapped!
        if item in self.__wrapped_type__.__dict__:
            return attr

        return partial(self._wrap_fun, me=self, fun_name=item)


def __init_wrapped__(self, *args, wrapped_type, driver_type, execute_concurrent, **kwargs):
    if '__init__' in wrapped_type.__dict__:
        wrapped_type.__init__(self, **kwargs)  # it has a __init__ method
    if 'channel' in kwargs:
        driver_type.__init__(self, kwargs['channel'])
    else:
        driver_type.__init__(self, *args)
    MultiChannelWrapper.__init__(self, driver_type, execute_concurrent)


def multi_driver(driver_class: Type[T2], execute_concurrent=False) -> Callable[[Type[T1]], Type[T2]]:
    """
    Decorator to define a driver for multiple sensors.

    The intended usage is:
    ```
    @multi_driver(driver_class)
    class my_multi_driver:
        ...
    ```
    The class my_multi_driver will be a new class that can be initialized with an instance of AbstractMultiChannel. It
    contains all methods of driver class. But each of these methods returns a tuple of responses one result for each
    channel in the AbstractMultiChannel.
    The wrapped class my_multi_driver may contain methods by its own. These methods will not be wrapped but executed
    like normal python methods.
    In case a __init__ method is needed, it has to contain a ** argument and the constructor of the wrapped type has to
    be called with named arguments including the channel argument of the driver_class constructor.

    :param driver_class: driver class to be wrapped in the new multi-driver class.
    :param execute_concurrent: Two modes of operation are possible. Whe executing a driver function, each driver is
    called sequentially when execute_concurrent is set to False.
    When execute_concurrent is set to True, a worker thread is
    spawned for each channel and the function is invoked on each thread individually. This method is appropriate when
    the commands to be executed may contain a long wait time before reading the response.

    :return: a new type that provides the above described functionalities.
    """

    def wrapper(new_class: Type[T1]) -> Type[T2]:
        # create the namespace for a new type
        namespace = dict(__init__=partialmethod(__init_wrapped__,
                                                wrapped_type=new_class,
                                                driver_type=driver_class,
                                                execute_concurrent=execute_concurrent),
                         __wrapped_type__=new_class)
        new_type = type(new_class.__name__, (new_class, driver_class, MultiChannelWrapper), namespace)
        return new_type

    return wrapper
