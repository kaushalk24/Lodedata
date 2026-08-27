"""OpenLode Design Assistant.

An open, working replica of the Lode Data *Design Assistant* workflow: a
computer-aided engineering system for the design and optimisation of broadband
(HFC / coaxial) distribution networks.

The package is deliberately dependency-free (Python standard library only) so
that it runs anywhere Python 3.10+ runs.

Layout
------
``lode.specs``   the seven specification files that drive every calculation
``lode.network`` the plant model (locations, spans, devices)
``lode.engine``  RF level cascade, performance, powering, auto-design
``lode.reports`` the printed/exported report suite
``lode.cli``     command line front end
``lode.web``     browser front end (Design Mode canvas + spec editors)
"""

__version__ = "1.0.0"
__all__ = ["specs", "network", "engine", "reports"]
