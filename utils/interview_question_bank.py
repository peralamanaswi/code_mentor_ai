"""Static interview question sets per language and difficulty (7–10 per category)."""

from __future__ import annotations

from typing import Dict, List, Tuple

CategoryKey = Tuple[str, str]

# Each category has 8 questions (within the 7–10 range requested).
QUESTION_BANK: Dict[CategoryKey, List[str]] = {
    ("Python", "Beginner"): [
        "What is a variable in Python? Why do we use meaningful names?",
        "Explain the difference between a list and a string in Python.",
        "How do you write a simple if-else statement? When would you use it?",
        "What is a function in Python? Why do programmers create functions?",
        "Why is indentation important in Python? What happens if it is wrong?",
        "What is the difference between print() and input() in a program?",
        "What is a loop? Name two loop types in Python and when to use each.",
        "What are try and except used for? Give a simple real-world example.",
    ],
    ("Python", "Intermediate"): [
        "Explain the difference between a list, tuple, and dictionary.",
        "What is list comprehension? Why is it useful?",
        "What is the difference between shallow copy and deep copy?",
        "How do *args and **kwargs work in function definitions?",
        "What is a decorator in Python? Describe one use case.",
        "Explain generators and why they save memory compared to lists.",
        "What is the Global Interpreter Lock (GIL)? How does it affect threading?",
        "How do you read and write files safely using a context manager (with)?",
    ],
    ("Python", "Advanced"): [
        "Compare multithreading vs multiprocessing in Python. When use each?",
        "What are metaclasses and when would a team actually need them?",
        "Explain async/await and how it differs from synchronous I/O.",
        "How does Python's garbage collection handle circular references?",
        "What are design patterns you would use in a large Python codebase?",
        "How do you profile and optimize slow Python code in production?",
        "Explain type hints, mypy, and how they improve maintainability.",
        "What security risks should you watch for in Python web APIs?",
    ],
    ("Java", "Beginner"): [
        "What is the difference between a class and an object in Java?",
        "Explain the difference between == and .equals() for objects.",
        "What are the primitive data types in Java? Give examples.",
        "What is the main method? Why does every Java program need one?",
        "What is the difference between public, private, and protected?",
        "How do if-else and switch statements differ? When use switch?",
        "What is an array in Java? How is it different from an ArrayList?",
        "What is an exception? How do try-catch blocks help?",
    ],
    ("Java", "Intermediate"): [
        "Explain inheritance and why Java uses it. Give a simple example.",
        "What is polymorphism? How do method overriding and overloading differ?",
        "What is the difference between an interface and an abstract class?",
        "Explain Java collections: List, Set, and Map — when to use each.",
        "What is encapsulation? How do getters and setters support it?",
        "What is the difference between String, StringBuilder, and StringBuffer?",
        "How does Java handle memory management and garbage collection?",
        "What are generics and why do they improve type safety?",
    ],
    ("Java", "Advanced"): [
        "Explain the Java Memory Model and happens-before relationships.",
        "Compare synchronized blocks, ReentrantLock, and concurrent collections.",
        "What is the difference between checked and unchecked exceptions?",
        "How does the JVM class loading mechanism work at a high level?",
        "What are common performance pitfalls in enterprise Java applications?",
        "Explain Stream API pipelines and when they beat traditional loops.",
        "How do you design thread-safe singletons? Compare common approaches.",
        "What security practices matter for Java REST APIs and JDBC?",
    ],
    ("C++", "Beginner"): [
        "What is the difference between compilation and execution in C++?",
        "Explain what a variable and data type are. Give examples.",
        "What is the difference between cin/cout and printf/scanf style I/O?",
        "What is a pointer? Why are pointers used in C++?",
        "What is the difference between stack and heap memory (simple terms)?",
        "How do if-else and loops work in C++? Name one loop type.",
        "What is a function? What is a function prototype?",
        "What is an array? How do you access elements safely?",
    ],
    ("C++", "Intermediate"): [
        "Explain the difference between pass-by-value and pass-by-reference.",
        "What is the difference between struct and class in C++?",
        "What are constructors and destructors? When are they called?",
        "Explain operator overloading with one practical example.",
        "What is the STL? Name three common STL containers.",
        "What is the difference between vector and array for dynamic data?",
        "What are smart pointers? Why prefer them over raw new/delete?",
        "What is const correctness and why does it matter?",
    ],
    ("C++", "Advanced"): [
        "Explain move semantics and rvalue references in modern C++.",
        "What is RAII and how does it prevent resource leaks?",
        "Compare virtual functions, vtables, and runtime polymorphism costs.",
        "What are template specialization and SFINAE (high-level)?",
        "How do you avoid undefined behavior in multithreaded C++?",
        "What is undefined behavior? Give three common C++ examples.",
        "When would you choose std::optional vs exceptions for errors?",
        "What are best practices for C++ performance on large codebases?",
    ],
    ("JavaScript", "Beginner"): [
        "What is the difference between let, const, and var?",
        "What are data types in JavaScript? Name primitive and one non-primitive.",
        "How do you select an HTML element using querySelector?",
        "What is an event listener? Give an example user interaction.",
        "What is the difference between == and ===?",
        "What is a function in JavaScript? Arrow vs regular function basics.",
        "What is an array method? Explain push and pop.",
        "What is JSON and why is it used in web apps?",
    ],
    ("JavaScript", "Intermediate"): [
        "Explain closures with a practical example.",
        "What is the event loop? How do callbacks and the call stack interact?",
        "What is the difference between null and undefined?",
        "Explain promises and async/await for asynchronous code.",
        "What is prototypal inheritance in JavaScript?",
        "How does this binding work in regular vs arrow functions?",
        "What is the DOM? How does the browser update the page?",
        "What are common ways to handle errors in async JavaScript?",
    ],
    ("JavaScript", "Advanced"): [
        "Explain microtasks vs macrotasks in the event loop.",
        "What are design patterns for scalable frontend architecture?",
        "How do you optimize bundle size and runtime performance?",
        "What is the difference between shallow and deep object cloning?",
        "How do you prevent XSS and CSRF in JavaScript web apps?",
        "Explain module systems: ES modules vs CommonJS trade-offs.",
        "What is hydration in SSR frameworks and why does it matter?",
        "How would you structure state in a large React/Vue application?",
    ],
}

DEFAULT_QUESTION_COUNT = 8


def get_questions_for_category(language: str, difficulty: str) -> List[str]:
    """Return 7–10 practice questions for the given language and difficulty."""
    questions = QUESTION_BANK.get((language, difficulty))
    if questions:
        return list(questions)
    return [
        f"Explain a core {language} concept suitable for {difficulty} level.",
        f"Describe how {language} handles memory or data at {difficulty} level.",
        f"What best practices should a {difficulty} {language} developer follow?",
        f"Compare two important features of {language} at {difficulty} level.",
        f"How would you debug a typical {difficulty}-level bug in {language}?",
        f"What tools or libraries help {language} developers at {difficulty} level?",
        f"Walk through how you would design a small {language} feature.",
        f"What interview topics are most common for {language} ({difficulty})?",
    ]


def get_category_label(language: str, difficulty: str) -> str:
    """Human-readable category name for UI headers."""
    return f"{language} · {difficulty}"
