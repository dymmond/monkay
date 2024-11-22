# Cages

Cages are a way to manage global states in an non-global maner.


## Usage

There are two methods

1. registering via self registering (recommended)
2. registering manually

The first way is recommended because it can be detected if it would nest another Cage object.
In this case it would just skip the initialization and the old Cage is kept.

Advantage of this: multiple libraries can patch other libraries without fearing to overwrite another cage.
