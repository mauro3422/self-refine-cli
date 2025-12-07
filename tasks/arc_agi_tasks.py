# ARC-AGI Style Tasks for Poetiq System
# Based on real ARC-AGI examples from https://github.com/fchollet/ARC-AGI
#
# These tasks require the LLM to:
# 1. Infer the transformation rule from training examples
# 2. Generate Python code to apply the rule
# 3. Pass verification against test cases

from core.code_verifier import PoetiqTask

# =============================================================================
# TASK 1: Matrix Rotation 180° (ARC-AGI: 3c9b0459)
# Rule: Rotate the 2D grid 180 degrees
# =============================================================================
ARC_ROTATE_180 = PoetiqTask(
    description="""Given a 2D grid (list of lists), return the grid rotated 180 degrees.

TRAINING EXAMPLES:
Input: [[2, 2, 1], [2, 1, 2], [2, 8, 1]]
Output: [[1, 8, 2], [2, 1, 2], [1, 2, 2]]

Input: [[9, 2, 4], [2, 4, 4], [2, 9, 2]]
Output: [[2, 9, 2], [4, 4, 2], [4, 2, 9]]

Input: [[8, 8, 8], [5, 5, 8], [8, 5, 5]]
Output: [[5, 5, 8], [8, 5, 5], [8, 8, 8]]

Implement a solve(grid) function that takes a 2D list and returns the rotated grid.""",
    test_cases=[
        {"input": [[6, 4, 4], [6, 6, 4], [4, 6, 7]], "expected": [[7, 6, 4], [4, 6, 6], [4, 4, 6]]},
        {"input": [[3, 2, 9], [9, 9, 9], [2, 3, 3]], "expected": [[3, 3, 2], [9, 9, 9], [9, 2, 3]]},
    ]
)


# =============================================================================
# TASK 2: Flip Grid Horizontally
# Rule: Mirror each row
# =============================================================================
ARC_FLIP_HORIZONTAL = PoetiqTask(
    description="""Given a 2D grid, flip it horizontally (mirror each row).

TRAINING EXAMPLES:
Input: [[1, 2, 3], [4, 5, 6]]
Output: [[3, 2, 1], [6, 5, 4]]

Input: [[1, 0], [0, 1]]
Output: [[0, 1], [1, 0]]

Implement a solve(grid) function.""",
    test_cases=[
        {"input": [[1, 2, 3], [4, 5, 6]], "expected": [[3, 2, 1], [6, 5, 4]]},
        {"input": [[7, 8, 9]], "expected": [[9, 8, 7]]},
        {"input": [[1]], "expected": [[1]]},
    ]
)


# =============================================================================
# TASK 3: Fill Non-Zero Values 
# Rule: For each row, if there's a non-zero value, fill the entire row with it
# =============================================================================
ARC_FILL_ROW = PoetiqTask(
    description="""Given a 2D grid where each row has at most one non-zero value,
fill each row completely with that non-zero value.

TRAINING EXAMPLES:
Input: [[0, 0, 5, 0], [3, 0, 0, 0], [0, 0, 0, 0]]
Output: [[5, 5, 5, 5], [3, 3, 3, 3], [0, 0, 0, 0]]

Input: [[0, 2], [0, 0], [1, 0]]
Output: [[2, 2], [0, 0], [1, 1]]

Implement a solve(grid) function.""",
    test_cases=[
        {"input": [[0, 0, 5, 0], [3, 0, 0, 0], [0, 0, 0, 0]], "expected": [[5, 5, 5, 5], [3, 3, 3, 3], [0, 0, 0, 0]]},
        {"input": [[0, 2], [0, 0], [1, 0]], "expected": [[2, 2], [0, 0], [1, 1]]},
        {"input": [[7]], "expected": [[7]]},
    ]
)


# =============================================================================
# TASK 4: Count Non-Zero and Return Grid
# Rule: Count non-zero elements, return 1x1 grid with count
# =============================================================================
ARC_COUNT_NONZERO = PoetiqTask(
    description="""Count the number of non-zero elements in a 2D grid and return a 1x1 grid with the count.

TRAINING EXAMPLES:
Input: [[0, 1, 0], [2, 0, 3]]
Output: [[3]]

Input: [[0, 0], [0, 0]]
Output: [[0]]

Implement a solve(grid) function.""",
    test_cases=[
        {"input": [[0, 1, 0], [2, 0, 3]], "expected": [[3]]},
        {"input": [[0, 0], [0, 0]], "expected": [[0]]},
        {"input": [[5, 5, 5]], "expected": [[3]]},
        {"input": [[0]], "expected": [[0]]},
    ]
)


# =============================================================================
# TASK 5: Transpose Grid
# Rule: Swap rows and columns
# =============================================================================
ARC_TRANSPOSE = PoetiqTask(
    description="""Transpose a 2D grid (swap rows and columns).

TRAINING EXAMPLES:
Input: [[1, 2, 3], [4, 5, 6]]
Output: [[1, 4], [2, 5], [3, 6]]

Input: [[1], [2], [3]]
Output: [[1, 2, 3]]

Implement a solve(grid) function.""",
    test_cases=[
        {"input": [[1, 2, 3], [4, 5, 6]], "expected": [[1, 4], [2, 5], [3, 6]]},
        {"input": [[1], [2], [3]], "expected": [[1, 2, 3]]},
        {"input": [[1, 2], [3, 4]], "expected": [[1, 3], [2, 4]]},
    ]
)


# =============================================================================
# TASK 6: Find Max in Each Row
# Rule: Return a column vector with max of each row
# =============================================================================
ARC_MAX_ROWS = PoetiqTask(
    description="""For each row in the grid, find the maximum value. Return as a column (list of single-element lists).

TRAINING EXAMPLES:
Input: [[1, 5, 2], [8, 3, 4]]
Output: [[5], [8]]

Input: [[9, 1], [2, 7], [5, 5]]
Output: [[9], [7], [5]]

Implement a solve(grid) function.""",
    test_cases=[
        {"input": [[1, 5, 2], [8, 3, 4]], "expected": [[5], [8]]},
        {"input": [[9, 1], [2, 7], [5, 5]], "expected": [[9], [7], [5]]},
        {"input": [[3]], "expected": [[3]]},
    ]
)


# All ARC-AGI tasks
ARC_AGI_TASKS = [
    ARC_ROTATE_180,
    ARC_FLIP_HORIZONTAL,
    ARC_FILL_ROW,
    ARC_COUNT_NONZERO,
    ARC_TRANSPOSE,
    ARC_MAX_ROWS,
]


def get_arc_task_by_name(name: str) -> PoetiqTask:
    """Get ARC task by name"""
    mapping = {
        "rotate": ARC_ROTATE_180,
        "flip": ARC_FLIP_HORIZONTAL,
        "fill": ARC_FILL_ROW,
        "count": ARC_COUNT_NONZERO,
        "transpose": ARC_TRANSPOSE,
        "max": ARC_MAX_ROWS,
    }
    return mapping.get(name, ARC_ROTATE_180)


if __name__ == "__main__":
    print("=== ARC-AGI Style Tasks ===\n")
    for i, task in enumerate(ARC_AGI_TASKS):
        print(f"{i+1}. {task.description[:60]}...")
        print(f"   Test cases: {len(task.test_cases)}")
        print()
