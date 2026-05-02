from .python import PythonGenerator

def get_generator(file_path):
    if file_path.endswith('.py'):
        return PythonGenerator()
    # Placeholder for future TreeSitter/JS support
    return None
