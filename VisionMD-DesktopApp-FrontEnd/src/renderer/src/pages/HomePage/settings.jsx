export default function Settings() {
  const quit = () => {
    /* For Electron: window.close(); for web: navigate away */
    window.close();
  };

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl">Settings</h2>
      <button
        onClick={quit}
        className="w-fit px-4 py-2 rounded bg-red-600 hover:bg-red-700"
      >
        Quit VisionMD
      </button>
    </div>
  );
}
