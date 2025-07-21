"""
Google Agent Assist MCP Server

This MCP server provides comprehensive access to all Google Agent Assist features including:
- Conversation management
- Conversation profiles
- Participants and real-time analysis
- Knowledge bases and documents
- Smart Reply models and training
- Article and FAQ suggestions
- Conversation summarization
- Generative AI features
"""

from typing import Any, Dict, List, Optional, Union
from mcp.server.fastmcp import FastMCP
from google.oauth2 import service_account
from google.cloud import dialogflow_v2 as dialogflow
from google.cloud import dialogflow_v2beta1 as dialogflow_beta
import json
import base64
from datetime import datetime

# Initialize FastMCP server
mcp = FastMCP("Google Agent Assist MCP Server")

# Global variables for client configuration
dialogflow_client = None
dialogflow_beta_client = None
credentials = None
project_id = None

@mcp.command("initialize_agent_assist")
def initialize_agent_assist(
    service_account_json: str,
    project_id_input: str,
    location: str = "global"
) -> Dict[str, Any]:
    """
    Initialize the Agent Assist client with service account credentials.
    
    :param service_account_json: JSON string containing service account credentials
    :param project_id_input: Google Cloud project ID
    :param location: Location for regional endpoints (default: "global")
    :return: Initialization status
    """
    global dialogflow_client, dialogflow_beta_client, credentials, project_id
    
    try:
        # Parse service account JSON
        service_account_info = json.loads(service_account_json)
        
        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        # Initialize clients
        dialogflow_client = dialogflow.ConversationsClient(credentials=credentials)
        dialogflow_beta_client = dialogflow_beta.ConversationsClient(credentials=credentials)
        
        project_id = project_id_input
        
        return {
            "status": "success",
            "message": "Agent Assist initialized successfully",
            "project_id": project_id,
            "location": location
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to initialize Agent Assist: {str(e)}"
        }

# ==================== Conversation Management ====================

@mcp.command("create_conversation")
def create_conversation(
    conversation_profile_id: str,
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new conversation.
    
    :param conversation_profile_id: ID of the conversation profile to use
    :param conversation_id: Optional custom conversation ID
    :return: Created conversation details
    """
    try:
        parent = f"projects/{project_id}/locations/global"
        conversation_profile = f"{parent}/conversationProfiles/{conversation_profile_id}"
        
        conversation = dialogflow.Conversation(
            conversation_profile=conversation_profile
        )
        
        if conversation_id:
            conversation.name = f"{parent}/conversations/{conversation_id}"
        
        response = dialogflow_client.create_conversation(
            parent=parent,
            conversation=conversation
        )
        
        return {
            "status": "success",
            "conversation": {
                "name": response.name,
                "lifecycle_state": response.lifecycle_state.name,
                "conversation_profile": response.conversation_profile,
                "start_time": response.start_time.isoformat() if response.start_time else None
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.command("list_conversations")
def list_conversations(
    page_size: int = 100,
    page_token: Optional[str] = None,
    filter_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    List conversations.
    
    :param page_size: Number of conversations to return
    :param page_token: Token for pagination
    :param filter_str: Filter string for conversations
    :return: List of conversations
    """
    try:
        parent = f"projects/{project_id}/locations/global"
        
        request = dialogflow.ListConversationsRequest(
            parent=parent,
            page_size=page_size,
            page_token=page_token,
            filter=filter_str
        )
        
        response = dialogflow_client.list_conversations(request=request)
        
        conversations = []
        for conv in response.conversations:
            conversations.append({
                "name": conv.name,
                "lifecycle_state": conv.lifecycle_state.name,
                "conversation_profile": conv.conversation_profile,
                "start_time": conv.start_time.isoformat() if conv.start_time else None,
                "end_time": conv.end_time.isoformat() if conv.end_time else None
            })
        
        return {
            "status": "success",
            "conversations": conversations,
            "next_page_token": response.next_page_token
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.command("complete_conversation")
def complete_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Complete a conversation.
    
    :param conversation_id: ID of the conversation to complete
    :return: Completed conversation details
    """
    try:
        name = f"projects/{project_id}/locations/global/conversations/{conversation_id}"
        
        response = dialogflow_client.complete_conversation(name=name)
        
        return {
            "status": "success",
            "conversation": {
                "name": response.name,
                "lifecycle_state": response.lifecycle_state.name,
                "end_time": response.end_time.isoformat() if response.end_time else None
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== Conversation Profiles ====================

@mcp.command("create_conversation_profile")
def create_conversation_profile(
    display_name: str,
    language_code: str = "en-US",
    time_zone: str = "America/New_York",
    human_agent_assistant_config: Optional[Dict[str, Any]] = None,
    automated_agent_config: Optional[Dict[str, Any]] = None,
    notification_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a conversation profile.
    
    :param display_name: Display name for the profile
    :param language_code: Language code (default: en-US)
    :param time_zone: Time zone (default: America/New_York)
    :param human_agent_assistant_config: Configuration for human agent assistance
    :param automated_agent_config: Configuration for automated agents
    :param notification_config: Configuration for notifications
    :return: Created conversation profile details
    """
    try:
        parent = f"projects/{project_id}/locations/global"
        
        profile = dialogflow.ConversationProfile(
            display_name=display_name,
            language_code=language_code,
            time_zone=time_zone
        )
        
        # Configure human agent assistant if provided
        if human_agent_assistant_config:
            profile.human_agent_assistant_config = _build_human_agent_assistant_config(
                human_agent_assistant_config
            )
        
        # Configure automated agent if provided
        if automated_agent_config:
            profile.automated_agent_config = dialogflow.AutomatedAgentConfig(
                agent=automated_agent_config.get("agent")
            )
        
        # Configure notifications if provided
        if notification_config:
            profile.notification_config = dialogflow.NotificationConfig(
                topic=notification_config.get("topic"),
                message_format=notification_config.get("message_format", "PROTO")
            )
        
        response = dialogflow_client.create_conversation_profile(
            parent=parent,
            conversation_profile=profile
        )
        
        return {
            "status": "success",
            "conversation_profile": {
                "name": response.name,
                "display_name": response.display_name,
                "create_time": response.create_time.isoformat() if response.create_time else None,
                "update_time": response.update_time.isoformat() if response.update_time else None
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _build_human_agent_assistant_config(config: Dict[str, Any]) -> Any:
    """Build HumanAgentAssistantConfig from dictionary."""
    ha_config = dialogflow.HumanAgentAssistantConfig()
    
    # Configure human agent suggestion config
    if "human_agent_suggestion_config" in config:
        suggestion_config = dialogflow.HumanAgentAssistantConfig.HumanAgentSuggestionConfig()
        
        # Add feature configs
        feature_configs = config["human_agent_suggestion_config"].get("feature_configs", [])
        for fc in feature_configs:
            feature_config = dialogflow.HumanAgentAssistantConfig.SuggestionFeatureConfig()
            
            # Set suggestion feature type
            feature_type = fc.get("type", "ARTICLE_SUGGESTION")
            feature_config.suggestion_feature = dialogflow.SuggestionFeature(
                type_=getattr(dialogflow.SuggestionFeature.Type, feature_type)
            )
            
            # Set query config
            if "query_config" in fc:
                query_config = dialogflow.HumanAgentAssistantConfig.SuggestionQueryConfig()
                
                # Knowledge base query source
                if "knowledge_base_query_source" in fc["query_config"]:
                    kb_source = fc["query_config"]["knowledge_base_query_source"]
                    query_config.knowledge_base_query_source = (
                        dialogflow.HumanAgentAssistantConfig.SuggestionQueryConfig.KnowledgeBaseQuerySource(
                            knowledge_bases=kb_source.get("knowledge_bases", [])
                        )
                    )
                
                # Document query source
                if "document_query_source" in fc["query_config"]:
                    doc_source = fc["query_config"]["document_query_source"]
                    query_config.document_query_source = (
                        dialogflow.HumanAgentAssistantConfig.SuggestionQueryConfig.DocumentQuerySource(
                            documents=doc_source.get("documents", [])
                        )
                    )
                
                # Dialogflow query source
                if "dialogflow_query_source" in fc["query_config"]:
                    df_source = fc["query_config"]["dialogflow_query_source"]
                    query_config.dialogflow_query_source = (
                        dialogflow.HumanAgentAssistantConfig.SuggestionQueryConfig.DialogflowQuerySource(
                            agent=df_source.get("agent")
                        )
                    )
                
                feature_config.query_config = query_config
            
            # Set other configs
            feature_config.max_results = fc.get("max_results", 3)
            feature_config.confidence_threshold = fc.get("confidence_threshold", 0.0)
            feature_config.enable_inline_suggestion = fc.get("enable_inline_suggestion", True)
            
            suggestion_config.feature_configs.append(feature_config)
        
        ha_config.human_agent_suggestion_config = suggestion_config
    
    # Configure message analysis config
    if "message_analysis_config" in config:
        ma_config = config["message_analysis_config"]
        ha_config.message_analysis_config = (
            dialogflow.HumanAgentAssistantConfig.MessageAnalysisConfig(
                enable_entity_extraction=ma_config.get("enable_entity_extraction", False),
                enable_sentiment_analysis=ma_config.get("enable_sentiment_analysis", False)
            )
        )
    
    return ha_config

@mcp.command("list_conversation_profiles")
def list_conversation_profiles(
    page_size: int = 100,
    page_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    List conversation profiles.
    
    :param page_size: Number of profiles to return
    :param page_token: Token for pagination
    :return: List of conversation profiles
    """
    try:
        parent = f"projects/{project_id}/locations/global"
        
        request = dialogflow.ListConversationProfilesRequest(
            parent=parent,
            page_size=page_size,
            page_token=page_token
        )
        
        response = dialogflow_client.list_conversation_profiles(request=request)
        
        profiles = []
        for profile in response.conversation_profiles:
            profiles.append({
                "name": profile.name,
                "display_name": profile.display_name,
                "language_code": profile.language_code,
                "time_zone": profile.time_zone,
                "create_time": profile.create_time.isoformat() if profile.create_time else None,
                "update_time": profile.update_time.isoformat() if profile.update_time else None
            })
        
        return {
            "status": "success",
            "conversation_profiles": profiles,
            "next_page_token": response.next_page_token
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== Participants ====================

@mcp.command("create_participant")
def create_participant(
    conversation_id: str,
    role: str = "END_USER",
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a participant in a conversation.
    
    :param conversation_id: ID of the conversation
    :param role: Role of the participant (END_USER, HUMAN_AGENT, AUTOMATED_AGENT)
    :param user_id: Optional user ID for the participant
    :return: Created participant details
    """
    try:
        parent = f"projects/{project_id}/locations/global/conversations/{conversation_id}"
        
        participant = dialogflow.Participant(
            role=getattr(dialogflow.Participant.Role, role)
        )
        
        if user_id:
            participant.user_id = user_id
        
        response = dialogflow_client.create_participant(
            parent=parent,
            participant=participant
        )
        
        return {
            "status": "success",
            "participant": {
                "name": response.name,
                "role": response.role.name,
                "user_id": response.user_id
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.command("analyze_content")
def analyze_content(
    participant_id: str,
    text_input: Optional[str] = None,
    audio_input: Optional[str] = None,
    event_input: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    enable_partial_automated_agent_reply: bool = False
) -> Dict[str, Any]:
    """
    Analyze content from a participant and get suggestions.
    
    :param participant_id: Full participant resource name
    :param text_input: Text message from participant
    :param audio_input: Base64 encoded audio from participant
    :param event_input: Event input dictionary
    :param request_id: Optional request ID for idempotency
    :param enable_partial_automated_agent_reply: Enable partial automated replies
    :return: Analysis results with suggestions
    """
    try:
        # Use beta client for full Agent Assist features
        request = dialogflow_beta.AnalyzeContentRequest(
            participant=participant_id
        )
        
        # Set input type
        if text_input:
            request.text_input = dialogflow_beta.TextInput(text=text_input)
        elif audio_input:
            request.audio_input = dialogflow_beta.AudioInput(
                audio=base64.b64decode(audio_input),
                config=dialogflow_beta.InputAudioConfig(
                    audio_encoding=dialogflow_beta.AudioEncoding.AUDIO_ENCODING_LINEAR_16,
                    sample_rate_hertz=16000,
                    language_code="en-US"
                )
            )
        elif event_input:
            request.event_input = dialogflow_beta.EventInput(
                name=event_input.get("name"),
                parameters=event_input.get("parameters", {}),
                language_code=event_input.get("language_code", "en-US")
            )
        
        # Set other parameters
        if request_id:
            request.request_id = request_id
        
        request.enable_partial_automated_agent_reply = enable_partial_automated_agent_reply
        
        # Call the API
        response = dialogflow_beta_client.analyze_content(request=request)
        
        # Process response
        result = {
            "status": "success",
            "reply_text": response.reply_text,
            "reply_audio": base64.b64encode(response.reply_audio.audio).decode() if response.reply_audio else None
        }
        
        # Add human agent suggestions
        if response.human_agent_suggestion_results:
            suggestions = []
            for suggestion in response.human_agent_suggestion_results:
                sugg_dict = {
                    "type": suggestion.suggestion_feature.type_.name
                }
                
                # Handle different suggestion types
                if hasattr(suggestion, 'article_answers'):
                    sugg_dict["article_answers"] = [
                        {
                            "title": answer.title,
                            "uri": answer.uri,
                            "snippets": answer.snippets,
                            "answer_record": answer.answer_record
                        }
                        for answer in suggestion.article_answers
                    ]
                elif hasattr(suggestion, 'faq_answers'):
                    sugg_dict["faq_answers"] = [
                        {
                            "answer": answer.answer,
                            "question": answer.question,
                            "source": answer.source,
                            "answer_record": answer.answer_record
                        }
                        for answer in suggestion.faq_answers
                    ]
                elif hasattr(suggestion, 'smart_reply_answers'):
                    sugg_dict["smart_reply_answers"] = [
                        {
                            "reply": answer.reply,
                            "confidence": answer.confidence,
                            "answer_record": answer.answer_record
                        }
                        for answer in suggestion.smart_reply_answers
                    ]
                
                suggestions.append(sugg_dict)
            
            result["human_agent_suggestions"] = suggestions
        
        # Add automated agent reply if present
        if response.automated_agent_reply:
            result["automated_agent_reply"] = {
                "response_messages": [
                    msg.text.text[0] if msg.text else None
                    for msg in response.automated_agent_reply.response_messages
                ],
                "intent": response.automated_agent_reply.intent.display_name if response.automated_agent_reply.intent else None,
                "parameters": dict(response.automated_agent_reply.parameters) if response.automated_agent_reply.parameters else {}
            }
        
        # Add message info
        if response.message:
            result["message"] = {
                "name": response.message.name,
                "content": response.message.content,
                "participant": response.message.participant,
                "participant_role": response.message.participant_role.name,
                "create_time": response.message.create_time.isoformat() if response.message.create_time else None
            }
        
        return result
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== Knowledge Bases ====================

@mcp.command("create_knowledge_base")
def create_knowledge_base(
    display_name: str,
    language_code: str = "en-US"
) -> Dict[str, Any]:
    """
    Create a knowledge base for storing documents.
    
    :param display_name: Display name for the knowledge base
    :param language_code: Language code (default: en-US)
    :return: Created knowledge base details
    """
    try:
        parent = f"projects/{project_id}/locations/global"
        
        knowledge_base = dialogflow.KnowledgeBase(
            display_name=display_name,
            language_code=language_code
        )
        
        kb_client = dialogflow.KnowledgeBasesClient(credentials=credentials)
        response = kb_client.create_knowledge_base(
            parent=parent,
            knowledge_base=knowledge_base
        )
        
        return {
            "status": "success",
            "knowledge_base": {
                "name": response.name,
                "display_name": response.display_name,
                "language_code": response.language_code
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.command("list_knowledge_bases")
def list_knowledge_bases(
    page_size: int = 100,
    page_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    List knowledge bases.
    
    :param page_size: Number of knowledge bases to return
    :param page_token: Token for pagination
    :return: List of knowledge bases
    """
    try:
        parent = f"projects/{project_id}/locations/global"
        
        kb_client = dialogflow.KnowledgeBasesClient(credentials=credentials)
        
        request = dialogflow.ListKnowledgeBasesRequest(
            parent=parent,
            page_size=page_size,
            page_token=page_token
        )
        
        response = kb_client.list_knowledge_bases(request=request)
        
        knowledge_bases = []
        for kb in response.knowledge_bases:
            knowledge_bases.append({
                "name": kb.name,
                "display_name": kb.display_name,
                "language_code": kb.language_code
            })
        
        return {
            "status": "success",
            "knowledge_bases": knowledge_bases,
            "next_page_token": response.next_page_token
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.command("create_document")
def create_document(
    knowledge_base_id: str,
    display_name: str,
    mime_type: str,
    knowledge_types: List[str],
    content_uri: Optional[str] = None,
    raw_content: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a document in a knowledge base.
    
    :param knowledge_base_id: ID of the knowledge base
    :param display_name: Display name for the document
    :param mime_type: MIME type of the document
    :param knowledge_types: List of knowledge types (FAQ, EXTRACTIVE_QA, ARTICLE_SUGGESTION)
    :param content_uri: URI of the document (for external documents)
    :param raw_content: Raw content of the document (for inline documents)
    :param metadata: Optional metadata for the document
    :return: Created document details
    """
    try:
        parent = f"projects/{project_id}/locations/global/knowledgeBases/{knowledge_base_id}"
        
        document = dialogflow.Document(
            display_name=display_name,
            mime_type=mime_type,
            knowledge_types=[getattr(dialogflow.Document.KnowledgeType, kt) for kt in knowledge_types]
        )
        
        if content_uri:
            document.content_uri = content_uri
        elif raw_content:
            document.raw_content = raw_content.encode('utf-8')
        
        if metadata:
            document.metadata = metadata
        
        doc_client = dialogflow.DocumentsClient(credentials=credentials)
        operation = doc_client.create_document(
            parent=parent,
            document=document
        )
        
        # Wait for operation to complete
        response = operation.result()
        
        return {
            "status": "success",
            "document": {
                "name": response.name,
                "display_name": response.display_name,
                "mime_type": response.mime_type,
                "knowledge_types": [kt.name for kt in response.knowledge_types]
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== Smart Reply ====================

@mcp.command("create_conversation_model")
def create_conversation_model(
    display_name: str,
    datasets: List[str],
    language_code: str = "en-US"
) -> Dict[str, Any]:
    """
    Create a Smart Reply conversation model.
    
    :param display_name: Display name for the model
    :param datasets: List of conversation dataset IDs
    :param language_code: Language code for the model
    :return: Created conversation model details
    """
    try:
        parent = f"projects/{project_id}/locations/global"
        
        # Create model with datasets
        input_datasets = []
        for dataset_id in datasets:
            input_datasets.append(
                dialogflow.InputDataset(
                    dataset=f"{parent}/conversationDatasets/{dataset_id}"
                )
            )
        
        model = dialogflow.ConversationModel(
            display_name=display_name,
            language_code=language_code,
            datasets=input_datasets
        )
        
        model_client = dialogflow.ConversationModelsClient(credentials=credentials)
        operation = model_client.create_conversation_model(
            parent=parent,
            conversation_model=model
        )
        
        # Note: Model creation is a long-running operation
        return {
            "status": "success",
            "message": "Model creation started",
            "operation_name": operation.name
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.command("deploy_conversation_model")
def deploy_conversation_model(model_id: str) -> Dict[str, Any]:
    """
    Deploy a conversation model.
    
    :param model_id: ID of the model to deploy
    :return: Deployment status
    """
    try:
        name = f"projects/{project_id}/locations/global/conversationModels/{model_id}"
        
        model_client = dialogflow.ConversationModelsClient(credentials=credentials)
        operation = model_client.deploy_conversation_model(name=name)
        
        return {
            "status": "success",
            "message": "Model deployment started",
            "operation_name": operation.name
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== Answer Records (Feedback) ====================

@mcp.command("update_answer_record")
def update_answer_record(
    answer_record_id: str,
    clicked: Optional[bool] = None,
    displayed: Optional[bool] = None,
    correctness_level: Optional[str] = None,
    feedback_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update an answer record with feedback.
    
    :param answer_record_id: Full answer record resource name
    :param clicked: Whether the suggestion was clicked
    :param displayed: Whether the suggestion was displayed
    :param correctness_level: Correctness level (FULLY_CORRECT, PARTIALLY_CORRECT, NOT_CORRECT)
    :param feedback_details: Additional feedback details
    :return: Updated answer record
    """
    try:
        answer_record = dialogflow.AnswerRecord(name=answer_record_id)
        
        # Build answer feedback
        feedback = dialogflow.AnswerFeedback()
        
        if clicked is not None:
            feedback.clicked = clicked
        
        if displayed is not None:
            feedback.displayed = displayed
        
        if correctness_level:
            feedback.correctness_level = getattr(
                dialogflow.AnswerFeedback.CorrectnessLevel,
                correctness_level
            )
        
        if feedback_details:
            # Add any custom feedback details
            feedback.agent_assistant_detail_feedback = feedback_details
        
        answer_record.answer_feedback = feedback
        
        # Update the answer record
        answer_records_client = dialogflow.AnswerRecordsClient(credentials=credentials)
        
        # Note: We need to specify which fields to update
        update_mask = []
        if clicked is not None:
            update_mask.append("answer_feedback.clicked")
        if displayed is not None:
            update_mask.append("answer_feedback.displayed")
        if correctness_level:
            update_mask.append("answer_feedback.correctness_level")
        if feedback_details:
            update_mask.append("answer_feedback.agent_assistant_detail_feedback")
        
        response = answer_records_client.update_answer_record(
            answer_record=answer_record,
            update_mask={"paths": update_mask}
        )
        
        return {
            "status": "success",
            "answer_record": {
                "name": response.name,
                "clicked": response.answer_feedback.clicked if response.answer_feedback else None,
                "displayed": response.answer_feedback.displayed if response.answer_feedback else None,
                "correctness_level": response.answer_feedback.correctness_level.name if response.answer_feedback and response.answer_feedback.correctness_level else None
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== Summarization ====================

@mcp.command("generate_conversation_summary")
def generate_conversation_summary(
    conversation_id: str,
    profile_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a summary for a conversation.
    
    :param conversation_id: ID of the conversation to summarize
    :param profile_id: Optional conversation profile ID with summarization config
    :return: Generated summary
    """
    try:
        conversation_name = f"projects/{project_id}/locations/global/conversations/{conversation_id}"
        
        # Use beta client for summarization features
        request = dialogflow_beta.SuggestConversationSummaryRequest(
            conversation=conversation_name
        )
        
        if profile_id:
            request.conversation_profile = f"projects/{project_id}/locations/global/conversationProfiles/{profile_id}"
        
        response = dialogflow_beta_client.suggest_conversation_summary(request=request)
        
        return {
            "status": "success",
            "summary": {
                "text": response.summary.text if response.summary else None,
                "text_sections": [
                    {
                        "text": section.text,
                        "topic": section.topic
                    }
                    for section in response.summary.text_sections
                ] if response.summary else [],
                "answer_record": response.summary.answer_record if response.summary else None
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== Conversation Datasets ====================

@mcp.command("create_conversation_dataset")
def create_conversation_dataset(
    display_name: str,
    description: Optional[str] = None,
    input_uri: Optional[str] = None,
    conversation_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a conversation dataset for training models.
    
    :param display_name: Display name for the dataset
    :param description: Optional description
    :param input_uri: GCS URI for conversation data
    :param conversation_info: Optional conversation metadata
    :return: Created dataset details
    """
    try:
        parent = f"projects/{project_id}/locations/global"
        
        dataset = dialogflow.ConversationDataset(
            display_name=display_name,
            description=description
        )
        
        if conversation_info:
            dataset.conversation_info = dialogflow.ConversationInfo(
                language_code=conversation_info.get("language_code", "en-US"),
                agent_id=conversation_info.get("agent_id")
            )
        
        dataset_client = dialogflow.ConversationDatasetsClient(credentials=credentials)
        
        request = dialogflow.CreateConversationDatasetRequest(
            parent=parent,
            conversation_dataset=dataset
        )
        
        operation = dataset_client.create_conversation_dataset(request=request)
        
        return {
            "status": "success",
            "message": "Dataset creation started",
            "operation_name": operation.name
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== Search Knowledge ====================

@mcp.command("search_knowledge")
def search_knowledge(
    query: str,
    conversation_profile_id: str,
    session_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    latest_message: Optional[str] = None,
    query_source: str = "AGENT_QUERY"
) -> Dict[str, Any]:
    """
    Search knowledge bases for answers.
    
    :param query: Search query
    :param conversation_profile_id: Conversation profile with knowledge config
    :param session_id: Optional session ID
    :param conversation_id: Optional conversation ID
    :param latest_message: Optional latest message for context
    :param query_source: Query source (AGENT_QUERY, SUGGESTED_QUERY)
    :return: Search results with answers
    """
    try:
        parent = f"projects/{project_id}/locations/global"
        
        # Build search knowledge request
        request = dialogflow_beta.SearchKnowledgeRequest(
            parent=parent,
            query=dialogflow_beta.TextInput(text=query, language_code="en-US"),
            conversation_profile=f"{parent}/conversationProfiles/{conversation_profile_id}"
        )
        
        if session_id:
            request.session_id = session_id
        
        if conversation_id:
            request.conversation = f"{parent}/conversations/{conversation_id}"
        
        if latest_message:
            request.latest_message = latest_message
        
        request.query_source = getattr(
            dialogflow_beta.SearchKnowledgeRequest.QuerySource,
            query_source
        )
        
        response = dialogflow_beta_client.search_knowledge(request=request)
        
        answers = []
        for answer in response.answers:
            answers.append({
                "faq_question": answer.faq_question,
                "answer": answer.answer,
                "confidence": answer.confidence,
                "source": answer.source,
                "metadata": dict(answer.metadata) if answer.metadata else {},
                "answer_record": answer.answer_record
            })
        
        return {
            "status": "success",
            "answers": answers,
            "rewritten_query": response.rewritten_query
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== Utility Functions ====================

@mcp.command("get_operation_status")
def get_operation_status(operation_name: str) -> Dict[str, Any]:
    """
    Get the status of a long-running operation.
    
    :param operation_name: Full operation name
    :return: Operation status and result
    """
    try:
        from google.longrunning import operations_pb2
        from google.api_core import operations_v1
        
        operations_client = operations_v1.OperationsClient(
            channel=dialogflow_client.transport.grpc_channel
        )
        
        operation = operations_client.get_operation(name=operation_name)
        
        result = {
            "status": "success",
            "operation": {
                "name": operation.name,
                "done": operation.done,
                "error": str(operation.error) if operation.error else None
            }
        }
        
        if operation.done and not operation.error:
            result["operation"]["result"] = "Operation completed successfully"
        
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.command("list_supported_languages")
def list_supported_languages() -> Dict[str, Any]:
    """
    List supported languages for Agent Assist.
    
    :return: List of supported language codes
    """
    # Agent Assist supports a subset of Dialogflow languages
    supported_languages = [
        {"code": "en-US", "name": "English (US)"},
        {"code": "en-GB", "name": "English (UK)"},
        {"code": "es-ES", "name": "Spanish (Spain)"},
        {"code": "es-419", "name": "Spanish (Latin America)"},
        {"code": "fr-FR", "name": "French"},
        {"code": "de-DE", "name": "German"},
        {"code": "it-IT", "name": "Italian"},
        {"code": "pt-BR", "name": "Portuguese (Brazil)"},
        {"code": "nl-NL", "name": "Dutch"},
        {"code": "ja-JP", "name": "Japanese"},
        {"code": "ko-KR", "name": "Korean"},
        {"code": "zh-CN", "name": "Chinese (Simplified)"},
        {"code": "zh-TW", "name": "Chinese (Traditional)"}
    ]
    
    return {
        "status": "success",
        "languages": supported_languages
    }

if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport='stdio')
