import Link from "next/link";

const Header = () => {
  return (
    <header className="relative flex items-center justify-between px-8 py-5 bg-gradient-to-r from-purple-800 to-indigo-800 z-10 border-b border-purple-700">
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>

      <div className="flex items-center relative">
        <div className="absolute -left-3 top-1/2 transform -translate-y-1/2 w-1.5 h-6 bg-teal-400 rounded-full opacity-80"></div>
        <span className="font-bold text-white text-xl tracking-tight">
          Chatter Box
        </span>
      </div>

      <div className="flex items-center space-x-1">
        <Link
          href={"/about"}
          className="text-white/80 text-xs px-4 py-2 font-medium hover:text-white hover:bg-white/10 rounded-lg transition-all duration-200 hover:cursor-pointer"
        >
          NEW CHAT
        </Link>
        <Link
          href={"/"}
          className="text-white bg-white/10 text-xs px-4 py-2 font-medium hover:bg-white/15 rounded-lg transition-all duration-200 cursor-pointer"
        >
          YOUR CHATS
        </Link>
        <a className="text-white/80 text-xs px-4 py-2 font-medium hover:text-white hover:bg-white/10 rounded-lg transition-all duration-200 cursor-pointer">
          CONTACTS
        </a>
        <a className="text-white/80 text-xs px-4 py-2 font-medium hover:text-white hover:bg-white/10 rounded-lg transition-all duration-200 cursor-pointer">
          SETTINGS
        </a>
      </div>
    </header>
  );
};

export default Header;
