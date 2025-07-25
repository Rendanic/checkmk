#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for check plug-ins"""

from __future__ import annotations

import enum
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import NamedTuple, overload, override, Self

# we may have 0/None for min/max for instance.
_OptionalPair = tuple[float | None, float | None] | None


class _KV(NamedTuple):
    name: str
    value: str


class _EvalableFloat(float):
    """Extends the float representation for Infinities in such way that
    they can be parsed by eval"""

    @override
    def __str__(self) -> str:
        return super().__repr__()

    @override
    def __repr__(self) -> str:
        if self > sys.float_info.max:
            return f"1e{sys.float_info.max_10_exp + 1}"
        if self < -1 * sys.float_info.max:
            return f"-1e{sys.float_info.max_10_exp + 1}"
        return super().__repr__()


class HostLabel(_KV):
    """Representing a host label in Checkmk

    This class creates a host label that can be yielded by a host_label_function as regisitered
    with the section.

        >>> my_label = HostLabel("my_key", "my_value")

    """

    __slots__ = ()

    def __new__(cls, name: str, value: str) -> Self:
        if not isinstance(name, str):
            raise TypeError(f"Invalid label name given: Expected string (got {name!r})")
        if not isinstance(value, str):
            raise TypeError(f"Invalid label value given: Expected string (got {value!r})")
        return super().__new__(cls, name, value)

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, {self.value!r})"


class ServiceLabel(_KV):
    """Representing a service label in Checkmk

    This class creates a service label that can be passed to a 'Service' object.
    It can be used in the discovery function to create a new label like this:

        >>> my_label = ServiceLabel("my_key", "my_value")

    """

    __slots__ = ()

    def __new__(cls, name: str, value: str) -> Self:
        if not isinstance(name, str):
            raise TypeError(f"Invalid label name given: Expected string (got {name!r})")
        if not isinstance(value, str):
            raise TypeError(f"Invalid label value given: Expected string (got {value!r})")
        return super().__new__(cls, name, value)

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, {self.value!r})"


class _ServiceTuple(NamedTuple):
    item: str | None
    parameters: Mapping[str, object]
    labels: Sequence[ServiceLabel]


class Service(_ServiceTuple):
    """Class representing services that the discover function yields

    Args:
        item:       The item of the service
        parameters: The determined discovery parameters for this service
        labels:     A list of labels attached to this service

    Example:

        >>> my_drive_service = Service(
        ...    item="disc_name",
        ...    parameters={},
        ... )

    """

    def __new__(
        cls,
        *,
        item: str | None = None,
        parameters: Mapping[str, object] | None = None,
        labels: Sequence[ServiceLabel] | None = None,
    ) -> Service:
        return super().__new__(
            cls,
            item=cls._parse_item(item),
            parameters=cls._parse_parameters(parameters),
            labels=cls._parse_labels(labels),
        )

    @staticmethod
    def _parse_item(item: str | None) -> str | None:
        if item is None:
            return None
        if item and isinstance(item, str):
            return item
        raise TypeError(f"'item' must be a non empty string or ommited entirely, got {item!r}")

    @staticmethod
    def _parse_parameters(parameters: Mapping[str, object] | None) -> Mapping[str, object]:
        if parameters is None:
            return {}
        if isinstance(parameters, dict) and all(isinstance(k, str) for k in parameters):
            return parameters
        raise TypeError(f"'parameters' must be dict or None, got {parameters!r}")

    @staticmethod
    def _parse_labels(labels: Sequence[ServiceLabel] | None) -> Sequence[ServiceLabel]:
        if not labels:
            return []
        if isinstance(labels, list) and all(isinstance(label, ServiceLabel) for label in labels):
            return labels
        raise TypeError(f"'labels' must be list of ServiceLabels or None, got {labels!r}")

    @override
    def __repr__(self) -> str:
        args = ", ".join(
            f"{k}={v!r}"
            for k, v in (
                ("item", self.item),
                ("parameters", self.parameters),
                ("labels", self.labels),
            )
            if v
        )
        return f"{self.__class__.__name__}({args})"


@enum.unique
class State(enum.Enum):
    """States of check results"""

    # Don't use IntEnum to prevent "state.CRIT < state.UNKNOWN" from evaluating to True.
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3

    def __int__(self) -> int:
        return int(self.value)

    @classmethod
    def best(cls, *args: State | int) -> State:
        """Returns the best of all passed states

        You can pass an arbitrary number of arguments, and the return value will be
        the "best" of them, where

            `OK -> WARN -> UNKNOWN -> CRIT`

        Args:
            args: Any number of one of State.OK, State.WARN, State.CRIT, State.UNKNOWN

        Returns:
            The best of the input states, one of State.OK, State.WARN, State.CRIT, State.UNKNOWN.

        Examples:
            >>> State.best(State.OK, State.WARN, State.CRIT, State.UNKNOWN)
            <State.OK: 0>
            >>> State.best(0, 1, State.CRIT)
            <State.OK: 0>
        """

        def _sort_key(s: State) -> int:
            match s:
                case cls.OK:
                    return 0
                case cls.WARN:
                    return 1
                case cls.UNKNOWN:
                    return 2
                case cls.CRIT:
                    return 3

        # we are nice and handle ints
        best = min(
            (cls(int(s)) for s in args),
            key=_sort_key,
        )

        return best

    @classmethod
    def worst(cls, *args: State | int) -> State:
        """Returns the worst of all passed states.

        You can pass an arbitrary number of arguments, and the return value will be
        the "worst" of them, where

            `OK < WARN < UNKNOWN < CRIT`

        Args:
            args: Any number of one of State.OK, State.WARN, State.CRIT, State.UNKNOWN

        Returns:
            The worst of the input States, one of State.OK, State.WARN, State.CRIT, State.UNKNOWN.

        Examples:
            >>> State.worst(State.OK, State.WARN, State.CRIT, State.UNKNOWN)
            <State.CRIT: 2>
            >>> State.worst(0, 1, State.CRIT)
            <State.CRIT: 2>
        """
        if cls.CRIT in args or 2 in args:
            return cls.CRIT
        return cls(max(int(s) for s in args))


class _MetricTuple(NamedTuple):
    name: str
    value: _EvalableFloat
    levels: tuple[_EvalableFloat | None, _EvalableFloat | None]
    boundaries: tuple[_EvalableFloat | None, _EvalableFloat | None]


class Metric(_MetricTuple):
    """Create a metric for a service

    Args:
        name:       The name of the metric.
                    Empty names or names containing spaces or any of the characters
                    ``:``, ``/`` or ``\\`` will raise an exception.
                    Metrics with names containing ``=`` or ``'`` will silently be dropped.
        value:      The measured value.
        levels:     A pair of upper levels, ie. warn and crit. This information is only used
                    for visualization by the graphing system. It does not affect the service state.
        boundaries: Additional information on the value domain for the graphing system.

    If you create a Metric in this way, you may want to consider using :func:`check_levels`.

    Example:

        >>> my_metric = Metric("used_slots_percent", 23.0, levels=(80, 90), boundaries=(0, 100))

    """

    def __new__(
        cls,
        name: str,
        value: float,
        *,
        levels: _OptionalPair = None,
        boundaries: _OptionalPair = None,
    ) -> Metric:
        cls._validate_name(name)

        if not isinstance(value, int | float):
            raise TypeError(f"value for metric must be float or int, got {value!r}")

        return super().__new__(
            cls,
            name=name,
            value=_EvalableFloat(value),
            levels=cls._sanitize_optionals("levels", levels),
            boundaries=cls._sanitize_optionals("boundaries", boundaries),
        )

    @staticmethod
    def _validate_name(metric_name: str) -> None:
        if not metric_name:
            raise TypeError("metric name must not be empty")

        # this is set is chosen such that the metric name would not be changed by `pnp_cleanup`
        if offenders := set(metric_name) & {" ", ":", "/", "\\"}:
            raise TypeError(f"invalid character(s) in metric name: {''.join(offenders)!r}")

    @staticmethod
    def _sanitize_single_value(field: str, value: float | None) -> _EvalableFloat | None:
        if value is None:
            return None
        if isinstance(value, int | float):
            return _EvalableFloat(value)
        raise TypeError(f"{field} values for metric must be float, int or None")

    @classmethod
    def _sanitize_optionals(
        cls,
        field: str,
        values: _OptionalPair,
    ) -> tuple[_EvalableFloat | None, _EvalableFloat | None]:
        if values is None:
            return None, None

        if not isinstance(values, tuple) or len(values) != 2:
            raise TypeError(f"{field!r} for metric must be a 2-tuple or None")

        return (
            cls._sanitize_single_value(field, values[0]),
            cls._sanitize_single_value(field, values[1]),
        )

    @override
    def __repr__(self) -> str:
        levels = "" if self.levels == (None, None) else f", levels={self.levels!r}"
        boundaries = "" if self.boundaries == (None, None) else f", boundaries={self.boundaries!r}"
        return f"{self.__class__.__name__}({self.name!r}, {self.value!r}{levels}{boundaries})"


class _ResultTuple(NamedTuple):
    state: State
    summary: str
    details: str


class Result(_ResultTuple):
    """A result to be yielded by check functions

    This is the class responsible for creating service output and setting the state of a service.

    Args:
        state:   The resulting state of the service.
        summary: The text to be displayed in the services *summary* view.
        notice:  A text that will only be shown in the *summary* if `state` is not OK.
        details: The alternative text that will be displayed in the details view. Defaults to the
                 value of `summary` or `notice`.

    Note:
        You must specify *exactly* one of the arguments ``summary`` and ``notice``!

    When yielding more than one result, Checkmk will not only aggregate the texts, but also
    compute the worst state for the service and highlight the individual non-OK states in
    the output.
    You should always match the state to the output, and yield subresults:

        >>> def my_check_function() -> None:
        ...     # the back end will comput the worst overall state:
        ...     yield Result(state=State.CRIT, summary="All the foos are broken")
        ...     yield Result(state=State.OK, summary="All the bars are fine")
        >>>
        >>> # run function to make sure we have a working example
        >>> _ = list(my_check_function())

    The ``notice`` keyword has the special property that it will only be displayed in the summary
    if the state passed to _this_ ``Result`` instance is not OK.
    Otherwise we assume it is sufficient to show the information in the details view:

        >>> def my_check_function() -> None:
        ...     count = 23
        ...     yield Result(
        ...         state=State.WARN if count <= 42 else State.OK,
        ...         notice=f"Things: {count}",  # only appear in summary if count drops below 43
        ...         details=f"We currently have this many things: {count}",
        ...     )
        >>>
        >>> # run function to make sure we have a working example
        >>> _ = list(my_check_function())

    If you find yourself computing the state by comparing a metric to some thresholds, you
    probably should be using :func:`check_levels`!

    """

    @overload
    def __new__(
        cls,
        *,
        state: State,
        summary: str,
        details: str | None = None,
    ) -> Result:
        pass

    @overload
    def __new__(
        cls,
        *,
        state: State,
        notice: str,
        details: str | None = None,
    ) -> Result:
        pass

    def __new__(  # type: ignore[no-untyped-def]
        cls,
        **kwargs,
    ) -> Result:
        state, summary, details = _create_result_fields(**kwargs)  # type: ignore[misc]
        return super().__new__(
            cls,
            state=state,
            summary=summary,
            details=details,
        )

    @override
    def __repr__(self) -> str:
        if not self.summary:
            text_args = f"notice={self.details!r}"
        elif self.summary != self.details:
            text_args = f"summary={self.summary!r}, details={self.details!r}"
        else:
            text_args = f"summary={self.summary!r}"
        return f"{self.__class__.__name__}(state={self.state!r}, {text_args})"


def _create_result_fields(
    *,
    state: State,
    summary: str | None = None,
    notice: str | None = None,
    details: str | None = None,
) -> tuple[State, str, str]:
    if not isinstance(state, State):
        raise TypeError(f"'state' must be a checkmk State constant, got {state}")

    for var, name in (
        (summary, "summary"),
        (notice, "notice"),
        (details, "details"),
    ):
        if var is None:
            continue
        if not isinstance(var, str):
            raise TypeError(f"'{name}' must be non-empty str or None, got {var}")
        if not var:
            raise ValueError(f"'{name}' must be non-empty str or None, got {var}")

    if summary:
        if notice:
            raise TypeError("'summary' and 'notice' are mutually exclusive arguments")
        if "\n" in summary:
            raise ValueError("'\\n' not allowed in 'summary'")
        return state, summary, details or summary

    if notice:
        summary = notice.replace("\n", ", ") if state != State.OK else ""
        return state, summary, details or notice

    raise TypeError("at least 'summary' or 'notice' is required")


class IgnoreResultsError(RuntimeError):
    """Raising an `IgnoreResultsError` from within a check function makes the service go stale.

    Example:

        >>> def check_db_table(item, section):
        ...     if item not in section:
        ...         # avoid a lot of UNKNOWN services:
        ...         raise IgnoreResultsError("Login to database failed")
        ...     # do your work here
        >>>

    """


class IgnoreResults:
    """A result to make the service go stale, but carry on with the check function

    Yielding a result of type `IgnoreResults` will have a similar effect as raising
    an :class:`.IgnoreResultsError`, with the difference that the execution of the
    check funtion will not be interrupted.

    .. code-block:: python

        yield IgnoreResults("Good luck next time!")
        return

    is equivalent to

    .. code-block:: python

        raise IgnoreResultsError("Good luck next time!")

    This is useful for instance if you want to initialize all counters, before
    returning.
    """

    def __init__(self, value: str = "currently no results") -> None:
        self._value = value

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._value!r})"

    @override
    def __str__(self) -> str:
        return self._value if isinstance(self._value, str) else repr(self._value)

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, IgnoreResults) and self._value == other._value


CheckResult = Iterable[IgnoreResults | Metric | Result]
DiscoveryResult = Iterable[Service]
