import ChatArea from "@/components/ChatArea";
import React from "react";

const NewChatPage = () => {
  return (
    <div className="flex justify-center py-8 px-4">
      {/* Main container with refined shadow and border */}
      <div className="w-[70%] rounded-xl shadow-lg border border-slate-700">
        <ChatArea previousMessages={[]} />
      </div>
    </div>
  );
};

export default NewChatPage;
