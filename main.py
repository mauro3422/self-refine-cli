# Entry point - Self-Refine CLI - SIMPLIFIED

import sys
import argparse
from modules.code_gen import CodeGenerator
from modules.data_analysis import DataAnalyzer
from modules.debugger import CodeDebugger
from utils.logger import RefineLogger
from utils.file_handler import FileHandler
from core.agent import Agent, init_tools


def print_banner():
    """Print CLI banner"""
    print("\n" + "="*60)
    print("🚀 Self-Refine CLI v2")
    print("   Arquitectura: Self-Refine + ReAct Agent")
    print("   Modelo: LFM2 via LM Studio")
    print("="*60)


def run_agent_mode():
    """Modo agente - ÚNICO MODO INTERACTIVO"""
    print_banner()
    
    init_tools()
    
    print("🤖 Agente Autónomo con Self-Refine")
    print("   • Todas las respuestas pasan por Self-Refine")
    print("   • Uso automático de herramientas cuando se necesitan")
    print("\n   Comandos: 'exit', 'clear', 'tools', 'help', 'memory'")
    print("-"*60)
    
    agent = Agent()
    
    while True:
        try:
            user_input = input("\n🧑 Tú: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 ¡Hasta luego!")
            break
        
        if not user_input:
            continue
        
        # Comandos especiales
        if user_input.lower() in ['exit', 'quit', 'salir']:
            print("👋 ¡Hasta luego!")
            break
        
        if user_input.lower() in ['clear', 'limpiar']:
            agent.clear_history()
            continue
        
        if user_input.lower() == 'tools':
            from tools.registry import get_registry
            print("\n" + get_registry().get_tools_description())
            continue
        
        if user_input.lower() == 'memory':
            from utils.memory import get_memory
            mem = get_memory()
            stats = mem.stats()
            print(f"\n📊 Memoria: {sum(stats.values())} lecciones guardadas")
            for t, c in stats.items():
                print(f"   {t}: {c}")
            continue
        
        if user_input.lower() == 'help':
            print("""
📖 Self-Refine CLI - Ayuda

El agente usa automáticamente:
  • read_file cuando pides leer archivos
  • list_dir cuando pides listar directorios
  • python_exec cuando pides ejecutar código
  • write_file cuando pides crear archivos

Cada respuesta pasa por Self-Refine:
  1. Genera respuesta
  2. Evalúa calidad (score /25)
  3. Si score < 22, refina iterativamente

EJEMPLOS:
  "lee el archivo README.md y resúmelo"
  "lista los archivos en tools/"
  "crea un script que calcule fibonacci en sandbox/"
  "ejecuta print(2+2)"
            """)
            continue
        
        # Ejecutar agente
        response = agent.run(user_input)
        print(f"\n🤖 Agente:\n{response}")


def run_command_mode(args):
    """Modo comando directo"""
    logger = RefineLogger()
    
    print_banner()
    
    result = None
    
    if args.mode == 'code':
        print(f"\n📝 Generando código...")
        gen = CodeGenerator()
        result = gen.generate_with_refinement(args.input)
        
    elif args.mode == 'analysis':
        print(f"\n📊 Analizando...")
        if not FileHandler.validate_file(args.input):
            print(f"❌ Archivo no encontrado: {args.input}")
            sys.exit(1)
        analyzer = DataAnalyzer()
        result = analyzer.analyze_csv(args.input, args.task)
        
    elif args.mode == 'debug':
        print(f"\n🐛 Debuggeando...")
        debugger = CodeDebugger()
        result = debugger.debug(args.input)
    
    if result:
        print("\n" + "="*60)
        print("🎯 RESULTADO:")
        print("="*60)
        print(result.get('final_output', result))
        if 'improvement_summary' in result:
            print(f"\n📈 {result['improvement_summary']}")


def main():
    parser = argparse.ArgumentParser(
        description='Self-Refine CLI - Agente con auto-mejora',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Uso:
  python main.py              # Modo interactivo (recomendado)
  python main.py code "tarea" # Generar código
  python main.py debug "code" # Debuggear
        """
    )
    
    parser.add_argument('mode', 
                        nargs='?',
                        choices=['code', 'analysis', 'debug'],
                        default=None)
    parser.add_argument('input', nargs='?', default='')
    parser.add_argument('--task', default='análisis general')
    
    args = parser.parse_args()
    
    if args.mode is None:
        run_agent_mode()
    else:
        if not args.input:
            print("❌ Se requiere input")
            sys.exit(1)
        run_command_mode(args)


if __name__ == "__main__":
    main()
