from flask import Flask, request, render_template, redirect
from ollama import chat
from db import get_db, init_db

app = Flask(__name__)

MODEL_NAME = "llama3.2:3b"

# inicializa banco
init_db()

# ======================
# ROTAS
# ======================

@app.route("/")
def home():
    conn = get_db()
    try:
        chats = conn.execute("SELECT * FROM chats ORDER BY id DESC").fetchall()
    finally:
        conn.close()

    return render_template("index.html", chats=chats, mensagens=[], chat_id=None)


@app.route("/novo", methods=["POST"])
def novo_chat():
    conn = get_db()
    try:
        cursor = conn.execute("INSERT INTO chats (titulo) VALUES ('Novo Chat')")
        chat_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()

    return redirect(f"/chat/{chat_id}")


@app.route("/chat/<int:chat_id>", methods=["GET", "POST"])
def chat_view(chat_id):
    conn = get_db()

    try:
        if request.method == "POST":
            pergunta = request.form.get("pergunta", "").strip()

            if not pergunta:
                return redirect(f"/chat/{chat_id}")

            historico = conn.execute(
                "SELECT pergunta, resposta FROM mensagens WHERE chat_id = ? ORDER BY id ASC",
                (chat_id,)
            ).fetchall()

            messages = [
                {"role": "system", "content": "Responda em português, de forma clara e coerente."}
            ]

            for m in historico:
                messages.append({"role": "user", "content": m["pergunta"]})
                messages.append({"role": "assistant", "content": m["resposta"]})

            messages.append({"role": "user", "content": pergunta})

            try:
                resultado = chat(
                    model=MODEL_NAME,
                    messages=messages,
                    think=False
                )
                resposta = resultado.message.content
            except Exception:
                resposta = "Erro ao gerar resposta da IA."

            # salva mensagem
            conn.execute(
                "INSERT INTO mensagens (chat_id, pergunta, resposta) VALUES (?, ?, ?)",
                (chat_id, pergunta, resposta)
            )

            # atualiza título do chat
            chat_atual = conn.execute(
                "SELECT titulo FROM chats WHERE id = ?",
                (chat_id,)
            ).fetchone()

            if chat_atual and chat_atual["titulo"] == "Novo Chat":
                titulo = pergunta.strip().replace("\n", " ")

                if len(titulo) > 40:
                    titulo = titulo[:40] + "..."

                conn.execute(
                    "UPDATE chats SET titulo = ? WHERE id = ?",
                    (titulo, chat_id)
                )

            conn.commit()

            return redirect(f"/chat/{chat_id}")

        # GET (carrega mensagens)
        mensagens = conn.execute(
            "SELECT * FROM mensagens WHERE chat_id = ?",
            (chat_id,)
        ).fetchall()

        chats = conn.execute(
            "SELECT * FROM chats ORDER BY id DESC"
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "index.html",
        chats=chats,
        mensagens=mensagens,
        chat_id=chat_id
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)