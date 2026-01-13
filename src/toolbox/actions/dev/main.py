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
        source: Annotated[Directory, Doc("O diretório 'src' do seu toolbox")],
    ) -> Directory:
        """
        Gera o esqueleto de uma nova action e registra automaticamente no main.py.
        """

        # 1. Cálculos de nomes
        class_name = "".join(word.title() for word in name.split("_"))
        base_path = f"toolbox/actions/{name}"
        main_py_path = "toolbox/main.py"

        # 2. Template: main.py da nova action (Construído linha por linha para segurança)
        # Isso evita erros de sintaxe com aspas triplas aninhadas.
        main_lines = [
            "import dagger",
            "from dagger import object_type, function, Directory, Container, dag, Doc, Secret",
            "from typing import Annotated, Optional",
            "",
            "@object_type",
            f"class {class_name}:",
            '    """',
            f"    Descrição da action {class_name}.",
            '    """',
            "",
            "    @function",
            "    def info(self) -> str:",
            '        """Retorna informações básicas sobre este módulo."""',
            f'        return "Action {name} pronta para uso!"',
            "",
        ]
        new_main_content = "\n".join(main_lines)

        # 3. Template: README.md
        readme_lines = [
            f"# 📦 {class_name} Actions",
            "",
            "Descrição do que este módulo faz.",
            "",
            "## 📋 Comandos",
            "",
            "### `info`",
            "Comando de verificação básico.",
            "",
            "```bash",
            f"dagger call {name} info",
            "```",
            "",
        ]
        readme_content = "\n".join(readme_lines)

        # 4. Ler e Modificar o main.py existente
        try:
            current_main = await source.file(main_py_path).contents()
        except Exception:
            raise Exception(f"Não foi possível ler {main_py_path}.")

        if "#FROMLINES" not in current_main:
            raise Exception(f"Marcador '#FROMLINES' não encontrado em {main_py_path}.")

        # Injeção do Import
        import_line = f"from .actions.{name}.main import {class_name}"
        new_content = current_main.replace("#FROMLINES", f"#FROMLINES\n{import_line}")

        # Injeção da Rota (Construído linha por linha para garantir indentação)
        route_lines = [
            "",
            "    @function",
            f"    def {name}(self) -> {class_name}:",
            f'        """Acessa as ferramentas de {name}."""',
            f"        return {class_name}()",
            "",
        ]
        new_content += "\n".join(route_lines)

        # 5. Retornar o Diretório com todos os arquivos
        return (
            source.with_new_file(f"{base_path}/__init__.py", "")
            .with_new_file(f"{base_path}/main.py", new_main_content)
            .with_new_file(f"{base_path}/README.md", readme_content)
            .with_new_file(main_py_path, new_content)
        )
