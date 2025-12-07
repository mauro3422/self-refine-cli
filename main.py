# Self-Refine CLI with Poetiq Parallel System
# Main entry point

import sys
import argparse
from core.poetiq import PoetiqRunner
from tools.file_tools import register_file_tools
from tools.command_tools import register_command_tools


from utils.logger import get_logger

def print_banner():
    print("\n" + "="*60)
    print("🚀 Self-Refine CLI v3 - Poetiq Edition")
    print("   Architecture: Parallel Workers + Voting")
    print("   Backend: llama.cpp GPU")
    print("="*60)


def init_system():
    """Initialize tools and return Poetiq runner"""
    print("\n🔧 Initializing...")
    register_file_tools()
    register_command_tools()
    runner = PoetiqRunner(num_workers=3)
    get_logger().log_info("System initialized and ready.")
    return runner


def run_interactive():
    """Interactive mode with Poetiq parallel system"""
    print_banner()
    
    runner = init_system()
    
    print("\n🤖 Poetiq Agent (3 parallel workers)")
    print("   Commands: 'exit', 'help'")
    print("-"*60)
    
    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Bye!")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() in ['exit', 'quit', 'salir']:
            print("👋 Bye!")
            break
        
        if user_input.lower() == 'help':
            print("""
📖 Poetiq CLI - Help

The system runs 3 parallel workers, votes on best response,
then executes the winning tool.

EXAMPLES:
  "list files in sandbox/"
  "create hello.py with print('Hello')"
  "read README.md"
            """)
            continue
        
        # Run Poetiq
        result = runner.run(user_input)
        
        print(f"\n🤖 Agent:\n{result['response']}")
        if result.get('tool_result'):
            print(f"\n📁 Tool output: {result['tool_result'][:200]}")


def run_single(task: str):
    """Single task mode"""
    print_banner()
    runner = init_system()
    result = runner.run(task)
    print(f"\n📝 Result:\n{result['response']}")


def main():
    parser = argparse.ArgumentParser(
        description='Self-Refine CLI with Poetiq Parallel System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage:
  python main.py              # Interactive mode
  python main.py "task"       # Single task
        """
    )
    
    parser.add_argument('task', nargs='?', default=None)
    parser.add_argument('--workers', '-w', type=int, default=3)
    
    args = parser.parse_args()
    
    if args.task:
        run_single(args.task)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
