# Example Poetiq Tasks with Test Cases
# Use these to test the verification loop

from core.code_verifier import PoetiqTask

# Collection of example tasks for testing
EXAMPLE_TASKS = [
    # Easy: String manipulation
    PoetiqTask.from_examples(
        description="Create a function that reverses a string",
        examples=[
            ("hello", "olleh"),
            ("world", "dlrow"),
            ("abc", "cba"),
            ("", ""),
        ]
    ),
    
    # Easy: Math
    PoetiqTask.from_examples(
        description="Create a function that doubles the input number",
        examples=[
            (1, 2),
            (5, 10),
            (0, 0),
            (-3, -6),
        ]
    ),
    
    # Medium: List operations
    PoetiqTask.from_examples(
        description="Create a function that returns the sum of all elements in a list",
        examples=[
            ([1, 2, 3], 6),
            ([10, 20], 30),
            ([], 0),
            ([5], 5),
        ]
    ),
    
    # Medium: String processing
    PoetiqTask.from_examples(
        description="Create a function that counts vowels in a string (a,e,i,o,u)",
        examples=[
            ("hello", 2),
            ("world", 1),
            ("aeiou", 5),
            ("xyz", 0),
        ]
    ),
    
    # Hard: Logic
    PoetiqTask.from_examples(
        description="Create a function that returns True if a number is prime, False otherwise",
        examples=[
            (2, True),
            (7, True),
            (4, False),
            (1, False),
            (17, True),
        ]
    ),
    
    # ARC-AGI style: Pattern transformation
    PoetiqTask.from_examples(
        description="Given a list, return a new list where each element is the original element + 1",
        examples=[
            ([1, 2, 3], [2, 3, 4]),
            ([0], [1]),
            ([-1, 0, 1], [0, 1, 2]),
            ([], []),
        ]
    ),
]


def get_task_by_difficulty(difficulty: str) -> PoetiqTask:
    """Get a task by difficulty level"""
    if difficulty == "easy":
        return EXAMPLE_TASKS[0]  # String reverse
    elif difficulty == "medium":
        return EXAMPLE_TASKS[2]  # List sum
    elif difficulty == "hard":
        return EXAMPLE_TASKS[4]  # Prime check
    else:
        return EXAMPLE_TASKS[0]


def get_random_task() -> PoetiqTask:
    """Get a random task"""
    import random
    return random.choice(EXAMPLE_TASKS)


if __name__ == "__main__":
    print("=== Example Poetiq Tasks ===\n")
    for i, task in enumerate(EXAMPLE_TASKS):
        print(f"{i+1}. {task.description}")
        print(f"   Tests: {len(task.test_cases)}")
        print(f"   Example: {task.test_cases[0]}")
        print()
