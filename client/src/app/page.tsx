import PreviousThreadList from "@/components/PreviousThreadList";
import { fetchPreviousThreads } from "@/utils/fetchPreviousThreads";

export interface SearchInfo {
  stages: string[];
  query: string;
  urls: string[] | string;
}

export interface Message {
  id: string;
  content: string;
  isUser: boolean;
  type: string;
  isLoading?: boolean;
  searchInfo?: SearchInfo;
}

export default async function Home() {
  const threadList = await fetchPreviousThreads();

  return (
    <div className="flex justify-center py-8 px-4">
      {/* Main container with refined shadow and border */}
      <div className="w-[70%] rounded-xl shadow-lg border border-slate-700">
        <PreviousThreadList threadList={threadList} />
      </div>
    </div>
  );
}
