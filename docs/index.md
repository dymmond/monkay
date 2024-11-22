# Home

## What is Monkay for?

Imagine a large software project which evolves. Old names should be deprecated. Imports
should be lazy so sideeffects are minimized.
But on the other hand you have self-registering parts like extensions or like Django models.

Multiple threads access application parts and tests with different settings are also a requirement
now things get really complicated.

This project solves the problems.
Monkay is a monkey-patcher with async features, preload and extension support (and some more).
Extension registrations can be reordered so there are also no dependency issues and extensions can build on each other.
Tests are possible by an async friendly approach via context variables so every situation can be easily tested.

For application frameworks Monkay provides settings which can also temporarily overwritten like in Django and
optionally setting names for preloads and extensions.

You may want to continue to the [Tutorial](tutorial.md)


## FAQ

### Monkay is a misspelling of monkey

I know. It is intentional.

First the name is quite unique and short.

Second the name monkey is already occupied.
