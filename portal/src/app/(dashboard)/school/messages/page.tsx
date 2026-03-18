"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { MessageSquare, Send } from "lucide-react";

export default function SchoolMessagesPage() {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Parent-Teacher Messages</h1>
        <p className="mt-1 text-sm text-gray-500">Communicate with parents about student AI safety</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="New Message" description="Send a note about a student">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Subject</label>
              <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Regarding AI usage in class..." className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Message</label>
              <textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write your message..." rows={4} className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <Button className="w-full"><Send className="mr-2 h-4 w-4" />Send Message</Button>
          </div>
        </Card>

        <Card title="Recent Messages">
          <div className="py-8 text-center">
            <MessageSquare className="mx-auto h-8 w-8 text-gray-300" />
            <p className="mt-2 text-sm text-gray-500">No messages yet</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
