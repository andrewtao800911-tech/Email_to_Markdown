import os
import json
import re

def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

def load_json_markers(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

# 移除形如 "0001 | 内容" 的行号前缀
prefix_pattern = re.compile(r'^\s*\d+\s*\|\s?(.*)$')

def remove_line_prefix(line):
    m = prefix_pattern.match(line)
    return m.group(1) if m else line

def clean_markdown_by_json(numbered_md_content, delete_blocks):
    """
    根据JSON标记删除原始markdown文件中的指定行，并收集删除的内容
    返回值：(清理后的内容, 删除的内容列表)
    """
    lines = numbered_md_content.splitlines()
    lines_to_delete = set()
    deleted_content = []

    for block in delete_blocks:
        # 直接使用JSON中提供的行号范围，不做任何额外判断
        start_line = int(block["start_line"])
        end_line = int(block["end_line"])
        block_type = block["type"]

        # 收集删除的内容
        block_deleted = []
        for idx in range(start_line - 1, end_line):
            if idx < len(lines):  # 防止超出文件实际行数
                lines_to_delete.add(idx)
                block_deleted.append(lines[idx])

        # 记录删除的内容块
        if block_deleted:
            deleted_content.append({
                "type": block_type,
                "start_line": start_line,
                "end_line": end_line,
                "content": block_deleted
            })

    # 保留未被标记删除的行
    kept_lines = [line for i, line in enumerate(lines) if i not in lines_to_delete]

    # 移除行号前缀
    cleaned_lines = [remove_line_prefix(line) for line in kept_lines]

    return "\n".join(cleaned_lines), deleted_content

def process_one_file(md_path, json_path, output_path, deleted_path):
    """
    处理单个文件：读取markdown和json，执行删除，保存结果和删除的内容
    """
    md_content = read_file(md_path)
    markers = load_json_markers(json_path)
    cleaned_content, deleted_content = clean_markdown_by_json(md_content, markers)
    
    # 保存清理后的内容
    write_file(output_path, cleaned_content)
    
    # 保存删除的内容
    if deleted_content:
        deleted_lines = []
        for block in deleted_content:
            deleted_lines.append(f"\n=== 删除块 [{block['type']}] 行号 {block['start_line']}-{block['end_line']} ===")
            deleted_lines.extend(block['content'])
        
        # 添加文件信息头
        header = f"# 删除内容记录 - {os.path.basename(md_path)}"
        header += f"\n## 原始文件: {md_path}"
        header += f"\n## JSON文件: {json_path}"
        
        deleted_full_content = "\n".join([header] + deleted_lines)
        write_file(deleted_path, deleted_full_content)
    
    print(f"处理完成: {output_path}")

def main():
    """
    批量处理所有文件
    """
    numbered_dir = "data/07_Numbered"
    json_dir = "data/07_Json"
    output_dir = "data/07_Cleaned"
    deleted_dir = "data/07_Deleted"  # 新增：用于存放删除的内容

    for root, _, files in os.walk(numbered_dir):
        for file in files:
            if not file.lower().endswith(".md"):
                continue

            md_path = os.path.join(root, file)
            rel_path = os.path.relpath(md_path, numbered_dir)
            json_path = os.path.join(json_dir, rel_path.replace(".md", ".json"))
            output_path = os.path.join(output_dir, rel_path)
            deleted_path = os.path.join(deleted_dir, rel_path.replace(".md", "_deleted.md"))

            if not os.path.exists(json_path):
                print(f"[跳过] 对应 JSON 不存在: {json_path}")
                continue

            process_one_file(md_path, json_path, output_path, deleted_path)

if __name__ == "__main__":
    main()
