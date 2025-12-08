#!/usr/bin/env python3
"""
Comprehensive failure analyzer for autonomous_loop.py output.
Extracts structured data from logs to identify patterns and lessons.
"""

import re
from collections import defaultdict
from datetime import datetime

LOG_FILE = "autonomous.log"

class TaskAnalysis:
    def __init__(self):
        self.tasks = []
        self.current_task = None
        self.error_patterns = defaultdict(int)
        self.score_distribution = defaultdict(int)
        
    def parse_log(self):
        """Parse the entire log file and extract structured data"""
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                line = line.strip()
                
                # New task detected
                if "Generated Task:" in line:
                    # Save previous task
                    if self.current_task:
                        self.tasks.append(self.current_task)
                    
                    # Start new task
                    task_match = re.search(r"Generated Task:\s*(.+)", line)
                    self.current_task = {
                        'description': task_match.group(1) if task_match else "Unknown",
                        'iterations': [],
                        'final_score': 0,
                        'errors': [],
                        'verification_feedback': []
                    }
                
                # Iteration scores
                elif self.current_task and re.search(r"Iter \d+: score=(\d+)/(\d+)", line):
                    match = re.search(r"Iter (\d+): score=(\d+)/(\d+)", line)
                    if match:
                        iter_num = int(match.group(1))
                        score = int(match.group(2))
                        max_score = int(match.group(3))
                        self.current_task['iterations'].append({
                            'iter': iter_num,
                            'score': score,
                            'max': max_score
                        })
                
                # Final score
                elif self.current_task and "Final score:" in line:
                    match = re.search(r"Final score:\s*(\d+)/(\d+)", line)
                    if match:
                        self.current_task['final_score'] = int(match.group(1))
                        self.score_distribution[int(match.group(1))] += 1
                
                # Error detection
                elif self.current_task and ("ERROR:" in line or "Error:" in line or "error:" in line):
                    self.current_task['errors'].append(line)
                    # Categorize error
                    if "Connection error" in line:
                        self.error_patterns["Connection/Network"] += 1
                    elif "syntax" in line.lower():
                        self.error_patterns["Syntax Error"] += 1
                    elif "import" in line.lower():
                        self.error_patterns["Import Error"] += 1
                    elif "timeout" in line.lower():
                        self.error_patterns["Timeout"] += 1
                    else:
                        self.error_patterns["Other Error"] += 1
                
                # Verification feedback (look for common verification messages)
                elif self.current_task and any(keyword in line.lower() for keyword in 
                    ["failed", "passed", "test", "assert", "expected"]):
                    self.current_task['verification_feedback'].append(line)
            
            # Don't forget the last task
            if self.current_task:
                self.tasks.append(self.current_task)
                
        except Exception as e:
            print(f"Parse error: {e}")
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        print("=" * 80)
        print("AUTONOMOUS LOOP - FAILURE ANALYSIS REPORT")
        print("=" * 80)
        print(f"\nTotal Tasks Attempted: {len(self.tasks)}")
        
        # Score distribution
        print("\n--- SCORE DISTRIBUTION ---")
        for score in sorted(self.score_distribution.keys()):
            count = self.score_distribution[score]
            bar = "█" * (count // 2)  # Visual bar
            print(f"Score {score}/25: {count:3d} tasks {bar}")
        
        # Error patterns
        print("\n--- ERROR PATTERNS ---")
        for error_type, count in sorted(self.error_patterns.items(), key=lambda x: -x[1]):
            print(f"{error_type:25s}: {count:3d} occurrences")
        
        # Task categories (simple keyword analysis)
        print("\n--- TASK CATEGORIES ---")
        categories = defaultdict(int)
        for task in self.tasks:
            desc = task['description'].lower()
            if 'test' in desc or 'unit' in desc:
                categories['Testing'] += 1
            elif 'validate' in desc or 'validation' in desc:
                categories['Validation'] += 1
            elif 'implement' in desc or 'create' in desc:
                categories['Implementation'] += 1
            elif 'refactor' in desc:
                categories['Refactoring'] += 1
            elif 'error' in desc:
                categories['Error/Failure'] += 1
            else:
                categories['Other'] += 1
        
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"{cat:20s}: {count:3d} tasks")
        
        # Detailed analysis of worst performers (score 0)
        print("\n" + "=" * 80)
        print("DETAILED FAILURE ANALYSIS (Score 0 Tasks)")
        print("=" * 80)
        
        zero_score_tasks = [t for t in self.tasks if t['final_score'] == 0]
        print(f"\nFound {len(zero_score_tasks)} tasks with 0/25 score")
        
        # Sample the first 3 and last 3 failures
        sample_tasks = zero_score_tasks[:3] + zero_score_tasks[-3:]
        
        for idx, task in enumerate(sample_tasks[:6], 1):
            print(f"\n--- Failure #{idx} ---")
            print(f"Task: {task['description'][:100]}")
            
            # Show iteration progression
            if task['iterations']:
                scores = [f"{it['score']}/{it['max']}" for it in task['iterations']]
                print(f"Score Progression: {' -> '.join(scores)}")
            
            # Show errors
            if task['errors']:
                print(f"Errors ({len(task['errors'])}):")
                for err in task['errors'][:2]:  # First 2 errors
                    print(f"  • {err[:80]}")
            
            # Show verification feedback
            if task['verification_feedback']:
                print(f"Verification feedback:")
                for fb in task['verification_feedback'][:2]:  # First 2 feedback items
                    print(f"  • {fb[:80]}")
        
        # Learning opportunities
        print("\n" + "=" * 80)
        print("ACTIONABLE INSIGHTS & LEARNING OPPORTUNITIES")
        print("=" * 80)
        
        insights = []
        
        # Insight 1: Connection errors
        if self.error_patterns.get("Connection/Network", 0) > 5:
            insights.append({
                'issue': 'Frequent Connection Errors',
                'count': self.error_patterns["Connection/Network"],
                'lesson': 'LLM server becomes unstable after extended use. Implement automatic reconnection or periodic server restart.',
                'action': 'Add retry logic with exponential backoff in LLMClient'
            })
        
        # Insight 2: Always scoring 0
        if self.score_distribution.get(0, 0) > len(self.tasks) * 0.8:
            insights.append({
                'issue': '80%+ tasks score 0/25',
                'count': self.score_distribution.get(0, 0),
                'lesson': 'Code verification is too strict OR generated code has systematic quality issues.',
                'action': 'Review CodeVerifier test generation. Consider lowering threshold for "partial success" (5/25 = basic syntax correct)'
            })
        
        # Insight 3: Score progression pattern
        improving_tasks = sum(1 for t in self.tasks if len(t['iterations']) >= 3 
                            and t['iterations'][-1]['score'] > t['iterations'][0]['score'])
        if improving_tasks > 0:
            insights.append({
                'issue': f'{improving_tasks} tasks showed improvement across iterations',
                'count': improving_tasks,
                'lesson': 'The refinement loop WORKS but hits a ceiling. Code improves iteration 1→5 but still fails final threshold.',
                'action': 'Analyze why iter5 code fails. May need better "hints" from failed test outputs.'
            })
        
        # Print insights
        for i, insight in enumerate(insights, 1):
            print(f"\n{i}. {insight['issue']}")
            print(f"   Frequency: {insight['count']}")
            print(f"   Learning: {insight['lesson']}")
            print(f"   ✓ Action: {insight['action']}")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    analyzer = TaskAnalysis()
    analyzer.parse_log()
    
    # Write to file instead of stdout
    import sys
    original_stdout = sys.stdout
    with open("failure_report.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        analyzer.generate_report()
        sys.stdout = original_stdout
    
    print("Report generated: failure_report.txt")
