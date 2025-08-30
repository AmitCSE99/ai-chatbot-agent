export async function fetchPreviousMessages() {
  try {
    const response = await fetch("http://127.0.0.1:8000/get-all");
    const json = await response.json();

    const messagesList = json.messages.map(
      (msg: { id: string; message_content: string; message_type: string }) => ({
        id: msg.id,
        content: msg.message_content,
        isUser: msg.message_type === "HumanMessage" ? true : false,
        type: "message",
      })
    );

    return messagesList;
  } catch (e: unknown) {
    console.error(e);
  }
}
