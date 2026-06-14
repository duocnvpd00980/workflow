
export interface Template {
  id: string;
  label: string;
  group: "blog" | "email" | "social" | "video" | "improve" | "rewrite" | "summarize" | "tone" | "expand" | "simplify";
  description?: string;
}

// export type GenerateFormState = {
//   prompt: string;
//   length: "short" | "medium" | "long";
//   tone: "professional" | "friendly" | "humorous";
//   language: "vi" | "en";
//   brandVoice: "default" | "custom";
//   ragDocs: string[];
//   framework: "free" | "aida" | "pas";
//   includeCta: boolean;
// };

export type ContentGroup =
  | "blog"
  | "email"
  | "social"
  | "video"
  | "improve"
  | "rewrite"
  | "summarize"
  | "tone"
  | "expand"
  | "simplify";

export interface Template {
  id: string;
  label: string;
  group: ContentGroup;
}

export interface GenerateFormState {
  prompt: string;
  length: "short" | "medium" | "long";
  tone: "professional" | "friendly" | "humorous";
  language: "vi" | "en";
  brandVoice: "default" | "custom";
  ragDocs: string[];
  framework: "free" | "aida" | "pas";
  includeCta: boolean;
}

export const CONTENT_GROUPS: {
  id: ContentGroup;
  emoji: string;
  label: string;
  sub: string;
}[] = [
  { id: "blog", emoji: "📝", label: "Blog & Web", sub: "Nội dung web, bài viết" },
  { id: "email", emoji: "📧", label: "Email & Sale", sub: "Email marketing, bán hàng" },
  { id: "social", emoji: "📱", label: "Social Media", sub: "Post, caption, hashtag" },
  { id: "video", emoji: "🎥", label: "Video & Audio", sub: "Script, podcast, YouTube" },
];

export const TOOL_GROUPS: {
  id: ContentGroup;
  emoji: string;
  label: string;
}[] = [
  { id: "improve", emoji: "📄", label: "Cải thiện" },
  { id: "rewrite", emoji: "🔄", label: "Viết lại" },
  { id: "summarize", emoji: "📋", label: "Tóm tắt" },
  { id: "tone", emoji: "🎭", label: "Đổi tone" },
  { id: "expand", emoji: "📈", label: "Mở rộng" },
  { id: "simplify", emoji: "🎯", label: "Đơn giản hóa" },
];

export const SUB_TEMPLATES: Record<ContentGroup, Template[]> = {
  blog: [
    { id: "blog-post", label: "Blog Post", group: "blog" },
    { id: "meta-seo", label: "Meta SEO", group: "blog" },
    { id: "product-desc", label: "Product Description", group: "blog" },
    { id: "faq", label: "FAQ", group: "blog" },
    { id: "website-copy", label: "Website Copy", group: "blog" },
  ],
  email: [
    { id: "cold-email", label: "Cold Email", group: "email" },
    { id: "newsletter", label: "Newsletter", group: "email" },
    { id: "follow-up", label: "Follow-up", group: "email" },
    { id: "promo-email", label: "Promo Email", group: "email" },
  ],
  social: [
    { id: "facebook-post", label: "Facebook Post", group: "social" },
    { id: "linkedin-post", label: "LinkedIn Post", group: "social" },
    { id: "instagram-caption", label: "Instagram Caption", group: "social" },
    { id: "twitter-thread", label: "Twitter Thread", group: "social" },
  ],
  video: [
    { id: "youtube-script", label: "YouTube Script", group: "video" },
    { id: "tiktok-script", label: "TikTok Script", group: "video" },
    { id: "podcast-outline", label: "Podcast Outline", group: "video" },
    { id: "video-ad", label: "Video Ad Script", group: "video" },
  ],
  improve: [{ id: "improve-text", label: "Cải thiện văn bản", group: "improve" }],
  rewrite: [{ id: "rewrite-text", label: "Viết lại nội dung", group: "rewrite" }],
  summarize: [{ id: "summarize-text", label: "Tóm tắt nội dung", group: "summarize" }],
  tone: [{ id: "change-tone", label: "Đổi giọng văn", group: "tone" }],
  expand: [{ id: "expand-text", label: "Mở rộng nội dung", group: "expand" }],
  simplify: [{ id: "simplify-text", label: "Đơn giản hóa", group: "simplify" }],
};

export const RAG_DOCS_OPTIONS = [
  { id: "guideline", label: "Brand Guideline" },
  { id: "research", label: "Research Docs" },
  { id: "product", label: "Product Info" },
];

export const defaultFormState: GenerateFormState = {
  prompt: "",
  length: "short",
  tone: "professional",
  language: "vi",
  brandVoice: "default",
  ragDocs: ["guideline", "research"],
  framework: "free",
  includeCta: true,
};