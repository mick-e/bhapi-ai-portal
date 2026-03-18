"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { BookOpen, Clock, ArrowRight, Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";

interface BlogPost {
  id: string;
  title: string;
  slug: string;
  excerpt: string;
  category: string;
  author: string;
  published_at: string;
  reading_time_minutes: number;
  tags: string[];
  content: string;
}

export default function BlogPage() {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<BlogPost | null>(null);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    const query = filter ? `?category=${filter}` : "";
    api.get<{ posts: BlogPost[] }>(`/api/v1/portal/blog${query}`)
      .then((d) => setPosts(d.posts))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filter]);

  if (selected) {
    return (
      <div>
        <button onClick={() => setSelected(null)} className="mb-4 text-sm text-primary-700 hover:text-primary-800">&larr; Back to blog</button>
        <article className="max-w-2xl">
          <h1 className="text-3xl font-bold text-gray-900">{selected.title}</h1>
          <div className="mt-2 flex items-center gap-3 text-sm text-gray-500">
            <span>{selected.author}</span>
            <span>&middot;</span>
            <span>{new Date(selected.published_at).toLocaleDateString()}</span>
            <span>&middot;</span>
            <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{selected.reading_time_minutes} min read</span>
          </div>
          <div className="mt-2 flex gap-2">{selected.tags.map((t) => (<span key={t} className="rounded-full bg-primary-100 px-2 py-0.5 text-xs text-primary-700">{t}</span>))}</div>
          <div className="mt-6 prose prose-sm text-gray-700"><p>{selected.content}</p></div>
        </article>
      </div>
    );
  }

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  const categories = [...new Set(posts.map((p) => p.category))];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Blog</h1>
        <p className="mt-1 text-sm text-gray-500">AI safety guides, compliance updates, and best practices</p>
      </div>

      <div className="mb-6 flex gap-2">
        <button onClick={() => setFilter("")} className={`rounded-full px-3 py-1 text-xs font-medium ${!filter ? "bg-primary-100 text-primary-700" : "bg-gray-100 text-gray-600"}`}>All</button>
        {categories.map((cat) => (
          <button key={cat} onClick={() => setFilter(cat)} className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${filter === cat ? "bg-primary-100 text-primary-700" : "bg-gray-100 text-gray-600"}`}>{cat}</button>
        ))}
      </div>

      <div className="space-y-4">
        {posts.map((post) => (
          <button key={post.id} onClick={() => setSelected(post)} className="w-full rounded-xl bg-white p-6 text-left shadow-sm ring-1 ring-gray-200 transition hover:ring-primary-300">
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="h-4 w-4 text-primary-600" />
              <span className="text-xs font-medium text-primary-600 capitalize">{post.category}</span>
              <span className="text-xs text-gray-400">&middot; {post.reading_time_minutes} min read</span>
            </div>
            <h2 className="text-lg font-bold text-gray-900">{post.title}</h2>
            <p className="mt-1 text-sm text-gray-500">{post.excerpt}</p>
            <div className="mt-3 flex items-center gap-1 text-sm font-medium text-primary-700">Read more <ArrowRight className="h-4 w-4" /></div>
          </button>
        ))}
      </div>
    </div>
  );
}
