import dagger
from dagger import object_type, function, Directory, Doc
from typing import Annotated

@object_type
class Dev:
    """
    Utilitários de desenvolvimento do Toolbox.
    Ajuda a criar esqueletos de novas actions e manter a estrutura do projeto.
    """

    @function
    async def new_action(
        self,
        name: Annotated[str, Doc("O nome da nova action (snake_case), ex: 'k8s_utils'")],
        source: Annotated[Directory, Doc("O diretório 'src' do seu toolbox")]
    ) -> Directory:
        """
        Gera o esqueleto de uma nova action e registra automaticamente no main.py.
        
        Requer que o arquivo 'src/toolbox/main.py' tenha o marcador '#FROMLINES'.
        
        Exemplo:
            dagger call dev new-action --name "kafka" --source src -o src
        """
        
        # 1. Cálculos de nomes
        # Transforma snake_case em PascalCase (ex: my_tool -> MyTool)
        class_name = "".join(word.title() for word in name.split('_'))
        base_path = f"toolbox/actions/{name}"
        main_py_path = "toolbox/main.py"

        # 2. Templates dos arquivos novos
        new_main_content = f"""import dagger
from dagger import object_type, function, Directory, Container, dag, Doc, Secret
from typing import Annotated, Optional

@object_type
class {class_name}:
    \"\"\"
    Descrição da action {class_name}.
    \"\"\"

    @function
    def info(self) -> str:
        \"\"\"Retorna informações básicas sobre este módulo.\"\"\"
        return "Action {name} pronta para uso!"
"""

        readme_content = f"""# 📦 {class_name} Actions

Descrição do que este módulo faz.

## 📋 Comandos

### `info`
Comando de verificação básico.

```bash
dagger call {name} info
"""
        # 3. Ler e Modificar o main.py
        # Lemos o conteúdo atual do arquivo no host
        try:
            current_main = await source.file(main_py_path).contents()
        except Exception:
            raise Exception(f"Não foi possível ler {main_py_path}. Verifique se o caminho está correto.")

        if "#FROMLINES" not in current_main:
            raise Exception(f"Marcador '#FROMLINES' não encontrado em {main_py_path}. Adicione-o antes dos imports das actions.")

        # Injeção do Import
        import_line = f"from .actions.{name}.main import {class_name}"
        # Adiciona o novo import logo abaixo do marcador
        new_content = current_main.replace(
            "#FROMLINES", 
            f"#FROMLINES\n{import_line}"
        )

        # Injeção da Rota (Append no final da classe)
        # Assume-se que a classe Toolbox é a última coisa no arquivo.
        # Adicionamos uma linha em branco e indentamos 4 espaços.
        route_code = f"""

@function
def {name}(self) -> {class_name}:
    \"\"\"Acessa as ferramentas de {name}.\"\"\"
    return {class_name}()
    
    """ 
        new_content += route_code
        # 4. Retornar o Diretório com todos os arquivos (novos e modificados)
        return (
            source
            .with_new_file(f"{base_path}/__init__.py", "")
            .with_new_file(f"{base_path}/main.py", new_main_content)
            .with_new_file(f"{base_path}/README.md", readme_content)
            .with_new_file(main_py_path, new_content)
        )