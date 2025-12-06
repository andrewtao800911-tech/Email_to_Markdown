import os

# Unified path handling

def get_unified_path(*paths):
    return os.path.normpath(os.path.join(*paths))

# Example usage
if __name__ == '__main__':
    path = get_unified_path('folder1', 'folder2', 'file.txt')
    print(f"Unified Path: {path}")