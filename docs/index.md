---
hide:
  - navigation
---

# Monkay

## What is Monkay?

**Monkay** is a powerful tool designed to address common challenges in complex software projects, especially those that evolve over time. It’s built to solve issues such as deprecated names, lazy imports, side effects, and the need for dynamic extension support.

In large projects, particularly when working with frameworks like Django, application components need to interact in a modular way. **Monkay** facilitates this by allowing the easy registration of extensions, flexible import handling, and dynamic configuration of settings—all while ensuring that there are no dependency conflicts, and that extensions can build on each other smoothly.

Some of the key features **Monkay** provides are:

- **Lazy imports**: Minimize side effects and ensure efficient resource management.
- **Self-registering extensions**: Similar to Django models, extensions can register themselves and be reordered without causing dependency issues.
- **Thread-safety**: Handle multiple threads accessing different parts of the application, ensuring consistency and stability.
- **Async-friendly testing**: Easily test applications with different settings and environments using **Monkay’s** context variables.
- **Dynamic settings management**: Overwrite settings temporarily, similar to how Django handles configurations.

With **Monkay**, testing becomes a breeze, and managing extensions and settings in dynamic, multithreaded applications is no longer a headache. It simplifies complex setups and allows you to focus on building rather than managing dependencies.

If you're ready to dive deeper, check out our [Tutorial](tutorial.md) to get started.

---

## Installation

To get started with **Monkay**, follow these installation steps:

### Step 1: Install Monkay

You can install **Monkay** via **pip** from PyPI:

```shell
pip install monkay
```

### Step 2: Python Version Requirement

**Monkay** requires Python 3.9 or later to function correctly. Ensure that you have the appropriate Python version installed:

```shell
python --version
```

If your Python version is below 3.9, you will need to upgrade to a compatible version.

---

## FAQ

### Why is Monkay called "Monkay"?

Yes, **Monkay** is a playful variation of "monkey." Here's why:

- **Unique and Memorable**: The name **Monkay** stands out and is easy to remember.
- **Trademark Issues**: "Monkey" is already widely used, so we opted for something distinct while still keeping the playful theme.

So, while it may look like a typo, it's entirely intentional—and a bit of fun too!
