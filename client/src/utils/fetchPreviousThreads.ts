export async function fetchPreviousThreads() {
  try {
    const response = await fetch("http://127.0.0.1:8000/get-threads");

    const json = await response.json();

    return json.thread_list;
  } catch (e: unknown) {
    console.error(e);
  }
}
