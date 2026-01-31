Contributing
============

Thank you for your interest in contributing to Secure Media Processor!

Getting Started
---------------

1. Fork the repository on GitHub
2. Clone your fork locally:

   .. code-block:: bash

      git clone https://github.com/YOUR_USERNAME/Secure-Media-Processor.git
      cd Secure-Media-Processor

3. Install development dependencies:

   .. code-block:: bash

      pip install -e ".[dev]"

4. Create a branch for your changes:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

Development Workflow
--------------------

Running Tests
~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=src --cov-report=html

   # Run specific test file
   pytest tests/test_azure_connector.py

Code Formatting
~~~~~~~~~~~~~~~

We use Black for code formatting:

.. code-block:: bash

   # Check formatting
   black --check src/ tests/

   # Auto-format
   black src/ tests/

Linting
~~~~~~~

.. code-block:: bash

   flake8 src/

Type Checking
~~~~~~~~~~~~~

.. code-block:: bash

   mypy src/

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs
   make html

Pull Request Guidelines
-----------------------

1. **Write tests** for new functionality
2. **Update documentation** for API changes
3. **Follow code style** (Black formatting, type hints)
4. **Write clear commit messages**
5. **Keep PRs focused** - one feature/fix per PR

Commit Message Format
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   type: Short description (50 chars max)

   Longer description if needed. Wrap at 72 characters.

   - Bullet points for multiple changes
   - Reference issues: Fixes #123

Types: ``feat``, ``fix``, ``docs``, ``test``, ``refactor``, ``chore``

Security Issues
---------------

If you discover a security vulnerability, please email directly instead of
opening a public issue. See SECURITY.md for details.

Code of Conduct
---------------

Be respectful and inclusive. We follow the Contributor Covenant.

Questions?
----------

Open an issue on GitHub or start a discussion.
