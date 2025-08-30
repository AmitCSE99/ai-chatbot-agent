import Link from "next/link";
import React from "react";

const PreviousThreadList = ({ threadList }: { threadList: string[] }) => {
  return (
    <div className="p-6 w-full flex flex-col gap-4">
      {threadList.map((thread) => (
        <Link
          key={thread}
          href={`/${thread}`}
          className="bg-slate-700 p-4 rounded-xl hover:bg-slate-800 cursor-pointer duration-200"
        >
          {thread}
        </Link>
      ))}
    </div>
  );
};

export default PreviousThreadList;
