import streamlit as st
from supabase import create_client, Client

# 1. Supabase 연동 설정 (내 Supabase 프로젝트 주소와 anon key로 변경해 주세요!)
SUPABASE_URL = "https://kktrkhfpxeavhaugzohd.supabase.co"
SUPABASE_KEY = "sb_publishable_c0dtskcvaF1CjK9fZwBm-g_XgRg6hXH"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.set_page_config(page_title="스마트 오답노트", layout="wide")

st.title("📊 취약점 분석 기능이 탑재된 스마트 오답노트")
st.caption("실시간으로 채점하고, 내가 어떤 개념 단원에 취약한지 차트로 분석해 줍니다.")

with st.sidebar:
    st.header("⚙️ 시험지 설정")
    exam_id = st.text_input("시험 ID 입력", value="2026_03_MATH")

st.subheader("✍️ 내 답안 마킹 (1번 ~ 20번)")
user_answers = {}

for row in range(5):
    cols = st.columns(4)
    for col_idx in range(4):
        q_num = row * 4 + col_idx + 1
        with cols[col_idx]:
            user_answers[str(q_num)] = st.text_input(f"{q_num}번 답", key=f"q_{q_num}", value="")

st.divider()

if st.button("🚀 전 문항 일괄 채점 및 분석하기", type="primary"):
    with st.spinner("클라우드 DB 조회 및 채점 중..."):
        try:
            # 2. Supabase에서 해당 시험의 정답 데이터 가져오기
            res = supabase.table("questions").select("*").eq("exam_id", exam_id).execute()
            questions = res.data
            
            if not questions:
                st.error("입력하신 시험 ID 정보가 없습니다.")
            else:
                # 3. 채점 및 오답노트 처리 로직
                wrong_questions = []
                correct_count = 0
                
                # 기존 오답 기록장(wrong_notes) 데이터도 함께 조회해서 싱크 맞추기
                notes_res = supabase.table("wrong_notes").select("*").eq("exam_id", exam_id).execute()
                saved_memos = {str(n["question_number"]): n["user_memo"] for n in notes_res.data}
                
                # 문제 순서 정렬
                questions.sort(key=lambda x: x["question_number"])
                
                for q in questions:
                    q_num_str = str(q["question_number"])
                    user_ans = user_answers.get(q_num_str, "").strip()
                    correct_ans = str(q["answer"]).strip()
                    
                    if user_ans == correct_ans:
                        correct_count += 1
                    else:
                        wrong_questions.append({
                            "question_number": q["question_number"],
                            "correct_answer": correct_ans,
                            "user_answer": user_ans if user_ans else "(미제출)",
                            "concept_tags": q.get("concept_tags", []),
                            "saved_memo": saved_memos.get(q_num_str, "")
                        })
                
                total_questions = len(questions)
                score_str = f"{correct_count}/{total_questions}"
                wrong_count = len(wrong_questions)
                
                # 4. 화면 결과 출력
                st.success(f"💯 채점 완료! 내 성적: {score_str}")
                
                if wrong_count == 0:
                    st.balloons()
                    st.info("와우! 만점입니다! 취약한 단원이 없습니다. 🎉")
                else:
                    # 취약 단원 분석 통계
                    tag_counts = {}
                    for item in wrong_questions:
                        for tag in item['concept_tags']:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
                    
                    if tag_counts:
                        st.subheader("📊 내 취약 개념 통계 분석")
                        st.caption("틀린 문제들의 개념 태그를 분석한 결과입니다.")
                        st.bar_chart(tag_counts, horizontal=True)
                    
                    st.divider()
                    
                    # 오답노트 리스트 출력
                    st.subheader(f"❌ 틀린 문제 오답 노트 ({wrong_count}문항)")
                    
                    for item in wrong_questions:
                        with st.container(border=True):
                            st.markdown(f"### ❓ {item['question_number']}번 문제")
                            st.markdown(f"**🏷️ 출제 개념:** {', '.join(item['concept_tags']) if item['concept_tags'] else '지정 없음'}")
                            st.error(f"내가 제출한 답: {item['user_answer']}  |  **실제 정답: {item['correct_answer']}**")
                            
                            st.divider()
                            
                            st.markdown("#### ✍️ 클라우드 오답 기록장")
                            user_memo = st.text_area(
                                "틀린 원인이나 풀이 팁을 적어두세요.", 
                                value=item['saved_memo'],
                                key=f"input_{exam_id}_{item['question_number']}"
                            )
                            
                            if st.button("💾 DB에 영구 저장하기", key=f"btn_{exam_id}_{item['question_number']}"):
                                # Supabase wrong_notes 테이블에 저장 (upsert 구조)
                                save_data = {
                                    "exam_id": exam_id,
                                    "question_number": item['question_number'],
                                    "user_memo": user_memo
                                }
                                # 기존 기록이 있으면 업데이트, 없으면 추가
                                supabase.table("wrong_notes").upsert(save_data, on_conflict="exam_id,question_number").execute()
                                st.toast(f"🎉 {item['question_number']}번 오답 메모가 영구 저장되었습니다!")
                                
        except Exception as e:
            st.error(f"클라우드 통신 실패: {e}")