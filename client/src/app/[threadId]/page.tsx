import ChatArea from "@/components/ChatArea";
import { fetchPreviousMessages } from "@/utils/fetchPreviousMessages";
import React from "react";

const ThreadPage = async ({ params }: { params: { threadId: string } }) => {
  const { threadId } = await params;
  const messages = await fetchPreviousMessages(threadId);

  return (
    <div className="flex justify-center py-8 px-4">
      {/* Main container with refined shadow and border */}
      <div className="w-[70%] rounded-xl shadow-lg border border-slate-700">
        <ChatArea previousMessages={messages} threadId={threadId} />
      </div>
    </div>
  );
};

export default ThreadPage;
