# warehouse_assistant/scripts/init_knowledge_base.py

import sys
import os
import glob
import logging
import traceback
from pathlib import Path

# 获取当前脚本文件所在的目录 (warehouse_assistant/scripts)
script_dir = Path(__file__).parent
# 获取项目根目录 (steel assistance)，即 scripts 目录的上两级目录
project_root = script_dir.parent

# 将项目根目录添加到 Python 模块搜索路径列表的开头
sys.path.insert(0, str(project_root))

print(f"Project root path: {project_root}")  # 添加在第12行后
print(f"Current sys.path: {sys.path}")       # 添加在第12行后

import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from warehouse_assistant.app.core.config import settings
from dotenv import load_dotenv

load_dotenv()

knowledge_base_dir = os.getenv("KNOWLEDGE_BASE_DIR")
chroma_persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY")

COLLECTION_NAME = "enterprise_knowledge_base"
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# --- 路径检查 (保持不变) ---
if not knowledge_base_dir or not os.path.exists(knowledge_base_dir):
    print(f"错误: 知识库路径 '{knowledge_base_dir}' 未设置或不存在。请检查环境变量 KNOWLEDGE_BASE_DIR。")
    exit()
elif not os.path.isdir(knowledge_base_dir):
     print(f"错误：配置的知识库路径 '{knowledge_base_dir}' 不是一个有效的目录。")
     exit()

if not chroma_persist_directory:
    print(f"错误: ChromaDB 存储路径未设置。请检查环境变量 CHROMA_PERSIST_DIRECTORY。")
    exit()

if not os.path.exists(chroma_persist_directory):
    print(f"信息: ChromaDB 存储路径 '{chroma_persist_directory}' 不存在，将自动创建。")
    try:
        os.makedirs(chroma_persist_directory)
    except OSError as e:
        print(f"错误：无法创建 ChromaDB 目录 '{chroma_persist_directory}'。错误：{e}")
        exit()

# --- 加载文档 (替代方案) ---
print(f"开始从目录 '{knowledge_base_dir}' 手动加载文档...")
documents = [] # 创建一个空列表来存储所有加载的文档
allowed_extensions = [".txt", ".md", ".pdf"] # 定义允许加载的文件类型

try:
    # 使用 glob 递归查找所有允许类型的文件
    # os.path.join 用于构建跨平台的路径
    # recursive=True 使得 ** 能匹配所有子目录
    file_paths = []
    for ext in allowed_extensions:
        # 注意：glob 需要正斜杠 / 作为路径分隔符，即使在 Windows 上
        search_pattern = os.path.join(knowledge_base_dir, '**', f'*{ext}').replace('\\', '/')
        found_files = glob.glob(search_pattern, recursive=True)
        file_paths.extend(found_files)
        print(f"找到 {len(found_files)} 个 '{ext}' 文件。")

    print(f"总共找到 {len(file_paths)} 个待处理文件。")

    # 遍历找到的每个文件路径
    for file_path in file_paths:
        try:
            # 获取文件扩展名
            _, extension = os.path.splitext(file_path)
            extension = extension.lower() # 转换为小写以匹配

            print(f"正在加载: {file_path}")
            loader = None # 初始化 loader 为 None

            # 根据扩展名选择加载器
            if extension == ".txt" or extension == ".md":
                loader = TextLoader(file_path, encoding="utf-8")
            elif extension == ".pdf":
                # 确保已安装 pypdf: pip install pypdf
                loader = PyPDFLoader(file_path)
            # 如果有其他类型，在这里添加 elif

            # 如果找到了合适的加载器，就加载文档
            if loader:
                loaded_docs = loader.load() # load() 返回文档列表
                documents.extend(loaded_docs) # 将加载的文档添加到总列表中
                print(f" -> 成功加载 {len(loaded_docs)} 个文档片段。")
            else:
                print(f" -> 跳过不支持的文件类型: {extension}")

        except ImportError as ie:
            # 捕捉特定于加载器的 ImportError，例如缺少 pypdf
             print(f"加载文件 {file_path} 时出错：缺少库。请确保安装了处理 '{extension}' 类型所需的库。错误: {ie}")
             # 可以选择继续处理下一个文件或退出
             # continue
        except Exception as file_load_error:
            # 捕捉加载单个文件时可能出现的其他错误
            print(f"加载文件 {file_path} 时发生错误: {file_load_error}")
            traceback.print_exc() # 打印详细错误信息
            # 决定是跳过这个文件还是中止整个过程
            # continue # 跳过这个文件

    print(f"\n成功加载了 {len(documents)} 个文档（或文档片段）。")
    if not documents and file_paths: # 如果找到了文件但没成功加载任何文档
        print("警告: 找到了文件，但未能成功加载任何文档内容。")
    elif not file_paths: # 如果一开始就没找到文件
         print("警告: 在指定目录中未找到任何支持类型的文件。")


except Exception as e:
    # 捕捉查找文件或循环过程中的未知错误
    print(f"处理文件列表时发生未知错误：{e}")
    traceback.print_exc()
    exit()

# --- 切割文档 (保持不变) ---
split_docs = [] # 初始化为空列表
if documents:
    print("开始切割文档...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True,
    )
    try:
        split_docs = text_splitter.split_documents(documents)
        print(f"成功切割成 {len(split_docs)} 个文本块。")
    except Exception as split_error:
        print(f"切割文档时出错: {split_error}")
        traceback.print_exc()
        # 决定是否继续，如果切割失败，后续步骤可能无意义
        # exit()
else:
    print("没有加载到文档内容，跳过切割步骤。")


# --- 初始化嵌入模型 (保持不变) ---
embeddings = None # 初始化为 None
if split_docs:
    print(f"初始化嵌入模型: {EMBEDDING_MODEL_NAME}")
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
        )
        print("嵌入模型初始化成功。")
    except Exception as e:
        print(f"初始化嵌入模型时出错：{e}")
        traceback.print_exc()
        exit()


# --- 初始化并填充 ChromaDB (保持不变，但确保 embeddings 有效) ---
if split_docs and embeddings: # 确保有文档块和有效的嵌入模型
    print(f"开始将文本块存入 ChromaDB (路径: {chroma_persist_directory}, 集合: {COLLECTION_NAME})...")
    try:
        vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=embeddings,
            collection_name=COLLECTION_NAME,
            persist_directory=chroma_persist_directory
        )
        vectorstore.persist()
        print(f"成功将 {len(split_docs)} 个文本块及其向量存入 ChromaDB 并持久化。")

        # --- 测试查询 (保持不变) ---
        print("\n执行测试查询...")
        test_query = "如何判断物料存储时间是否正常？"
        try:
            results = vectorstore.similarity_search(test_query, k=3)
            if results:
                print(f"对于查询 '{test_query}'，找到的相关内容：")
                for i, doc in enumerate(results):
                    print(f"--- 相关块 {i+1} ---")
                    print(f"来源: {doc.metadata.get('source', '未知')}")
                    print(f"内容片段: {doc.page_content[:300]}...")
            else:
                print(f"对于查询 '{test_query}', 没有找到相关内容。")
        except Exception as e:
            print(f"执行测试查询时出错: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"存储数据到 ChromaDB 时出错: {e}")
        print("尝试使用替代方法创建向量存储...")
        
        try:
            # 替代方法：先创建本地客户端和集合
            import chromadb
            client = chromadb.PersistentClient(path=chroma_persist_directory)
            # 删除可能已存在的同名集合
            try:
                client.delete_collection(COLLECTION_NAME)
                print(f"已删除可能存在的旧集合 '{COLLECTION_NAME}'")
            except:
                pass
            
            # 然后重新创建向量存储
            vectorstore = Chroma.from_documents(
                documents=split_docs,
                embedding=embeddings,
                collection_name=COLLECTION_NAME,
                persist_directory=chroma_persist_directory
            )
            print("使用替代方法成功创建向量存储")
        except Exception as e2:
            print(f"使用替代方法时也出错: {e2}")
            traceback.print_exc()

elif not split_docs:
     print("没有切割后的文档块，跳过存储到 ChromaDB 的步骤。")
elif not embeddings:
     print("嵌入模型未能成功初始化，跳过存储到 ChromaDB 的步骤。")


print("\n处理完成。")

