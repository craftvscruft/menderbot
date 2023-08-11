# Design

Menderbot was created to demonstrate the principles of the [Mechanized Mending Manifesto](https://mender.ai/docs/intro), summarized:

* The dominant challenge in software development is maintenance
* LLMs can help
* Humans, conventional algorithms, and LLMs have different strengths
  * They do not replace each other
  * Effective systems will carefully combine them

Following these principles, Menderbot aims to:

* Optimize for working on large existing codebases
* Treat LLM output as useful but untrustworthy
* Default to safety
* Play well with other automation

## Safeguards

* LLM output is always labeled
* Avoid using LLM output in executable code
* Require explicit consent to use LLM on repo
* **pending**: Price confirmation for batch operations

### LLM consent

Assume the user has multiple API keys and only one may be authorized.

### LLM output in code

Since LLM output is untrustworthy, we avoid using it to modify code where possible. Here are some safer uses.

* Comments, sanitized to prevent code injection
* Type annotations, sanitized and type-checked
* Refactoring suggestions executed by deterministic syntax-tree operations

## Language-aware

We plan to support these language families at minimum, with syntax awareness.

* JavaScript / TypeScript
* C / C++
* Java
* Python

## Technical decisions

### Python

Python is currently the defacto language for AI development, so it's a reasonable pick for an experimental AI project. However, other languages such as Go and Rust could make the distribution of a command-line tool easier.

### Antlr 
We use the [Antlr Python Target](https://github.com/antlr/antlr4/blob/master/doc/python-target.md) to parse source code so that we can make updates in consistent syntax-aware way.

Pros:
* Supports a wide variety of languages with community maintained grammars available
* Mature and widely adopted
* Allows us to stay in pure Python both at build and runtime

Cons:
* Not Python native, API very hairy to use compared to the 
* Requires running Java to re-generate code on grammar changes

Unknowns:
* Can we parse syntax errors and keep going in "the right way"?

#### tree-sitter (Runner Up)

Pros:
* Supports a wide variety of languages with community maintained grammars available
* Can parse files with syntax errors and keep going

Cons:
* Requires shipping with a platform-specific binary built from C

Other alternatives considered: 

Lark, LibCST (parsing Python)

