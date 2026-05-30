===========Bạn là AI Architect chuyên sâu về Multi-Agent Systems và LangGraph.

Nhiệm vụ của bạn:

KHÔNG được trả lời theo ý kiến cá nhân.

PHẢI đọc và phân tích tài liệu CHÍNH THỨC từ:

LangGraph official docs

OpenAI Agents SDK docs

Anthropic agent workflow docs

Microsoft Semantic Kernel docs

Sau đó hãy xác định:

Kiến trúc orchestration multi-agent nào đang được converge nhiều nhất hiện nay.

Pattern nào được xem là production-grade phổ biến nhất.

Các framework lớn có đang dùng cùng một tư duy kiến trúc không.

Yêu cầu cực kỳ quan trọng:

KHÔNG được đưa sơ đồ tự tưởng tượng.

PHẢI trích dẫn hoặc mô tả pattern thật từ docs chính hãng.

Chỉ tập trung vào:

Supervisor / Manager pattern

Specialized agents

Shared state

Aggregator / Reducer

Validator / Evaluator loops

Error handling

Durable execution

Human-in-the-loop

Sau khi phân tích:

Hãy tạo:

Mermaid diagram production-grade chuẩn nhất hiện nay

Giải thích:

Vì sao sơ đồ đó đang trở thành chuẩn de-facto

So sánh:

LangGraph

OpenAI Agents

Anthropic workflows

Semantic Kernel

Cuối cùng:

Kết luận xem các framework lớn hiện nay có đang hội tụ về mô hình:

Supervisor

-> Specialized Agents

-> Supervisor

hay không.

Yêu cầu:

Chỉ dùng thông tin từ docs chính thức.

Không dùng tutorial YouTube.

Không dùng blog random.

Ưu tiên source từ chính hãng.

Giải thích theo góc nhìn production architecture thật sự. ========================graph TD

    %% Entry Point

    User([User Request]) --> InputGuard[Input Guard]

    InputGuard --> Supervisor{Supervisor Agent}

    %% =========================

    %% Marketing Sub-Graph

    %% =========================

    Supervisor -->|Marketing Task| MktRouter{Mkt Router}

    

    subgraph BlogCrew [Blog Crew - 3 Nodes]

        ResearcherAgent[Researcher Agent] -->|Fact Sheet| WriterAgent[Writer Agent]

        WriterAgent -->|Draft| EditorAgent[Editor Agent]

        EditorAgent -->|Revision < 3| WriterAgent

    end

    

    MktRouter -->|Blog Post| ResearcherAgent

    EditorAgent -->|Approved Draft| Evaluator

    MktRouter -->|Social Ads| AdsAgent[Ads Agent]

    MktRouter -->|Visuals| ImageAgent[Image Gen Agent]

    

    %% =========================

    %% Other Flows

    %% =========================

    Supervisor -->|QA| QAAgent[QA Agent]

    

    %% Fast Track

    Supervisor -.->|Bypass| SmalltalkAgent[Smalltalk Agent]

    SmalltalkAgent --> FinalResponse

    %% =========================

    %% Evaluator Layer

    %% =========================

    AdsAgent --> Evaluator{Evaluator}

    ImageAgent --> Evaluator

    QAAgent --> Evaluator

    

    %% =========================

    %% Persistence & Flow Control

    %% =========================

    Evaluator -->|Fail| RetryPolicy[Local Retry Policy]

    RetryPolicy -.->|Re-run Node| Supervisor

    

    Evaluator -->|Pass| Aggregator[Aggregator / Reducer]

    Aggregator --> HumanReview{Human Approval}

    

    HumanReview -->|Rejected| Supervisor

    HumanReview -->|Approved| SharedState[(State / Memory)]

    SharedState --> FinalResponse[Final Response]

    FinalResponse --> User = ==================== [mermaid.live/]===================> graph TD
    %% Entry Point
    __start__ --> node_input_guard
    node_input_guard --> node_supervisor
    
    %% Control Plane & Routing
    node_supervisor -- knowledge --> node_knowledge
    node_supervisor -- marketing --> node_marketing
    node_supervisor -- smalltalk --> node_lightweight_chat
    
    %% Data Plane & Evaluation
    node_knowledge --> node_evaluator
    node_marketing --> node_evaluator
    
    %% Error Handling & Flow Control
    node_evaluator -- retry --> node_supervisor
    node_evaluator -- pass --> node_aggregator
    
    %% Output Pipeline & Human-in-the-loop
    node_aggregator --> node_output_guard
    node_output_guard --> node_human_review
    
    node_human_review -- rejected --> node_supervisor
    node_human_review -- approved --> node_shared_state
    
    %% Finalization
    node_shared_state --> node_final_response
    node_lightweight_chat --> node_final_response
    node_final_response --> __end__




=========================

__start__
   ↓
node_guard
  [validate input]
  [semantic cache check → hit: skip to node_finalize]
  [load user_profile + relevant_episodes → state]   ← thêm vào đây
   ↓
node_supervisor
  [đọc state["user_profile"], state["relevant_episodes"]]
  [route: knowledge / marketing / smalltalk]
   ↓ ...